# Copyright (C) 2009-2013, Sugar Labs
# Copyright (C) 2009, Tomeu Vizoso
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

import os
import logging
import time

from gi.repository import GObject
from gi.repository import GLib
from gi.repository import GConf

from sugar3.bundle import bundle_from_archive
from sugar3.bundle.bundleversion import NormalizedVersion

from jarabe.model import bundleregistry
from jarabe.util.downloader import Downloader

from jarabe.model.update import BundleUpdate, aslo

_logger = logging.getLogger('Updater')
_instance = None
_LAST_UPDATE_KEY = '/desktop/sugar/update/last_activity_update'
_UPDATE_FREQUENCY_KEY = '/desktop/sugar/update/auto_update_frequency'

STATE_IDLE = 0
STATE_CHECKING = 1
STATE_CHECKED = 2
STATE_DOWNLOADING = 3
STATE_UPDATING = 4


class UpdaterStateException(Exception):
    pass


class Updater(GObject.GObject):
    __gtype_name__ = 'SugarUpdater'

    __gsignals__ = {
        'updates-available': (GObject.SignalFlags.RUN_FIRST,
                              None,
                              (object,)),
        'progress': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     (int, str, float)),
        'finished': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     (object, object, bool))
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._updates = None
        self._bundles_to_check = None
        self._total_bundles_to_check = 0
        self._bundles_to_update = None
        self._total_bundles_to_update = 0
        self._bundle_update = None
        self._bundles_updated = None
        self._bundles_failed = None

        self._downloader = None
        self._cancelling = False
        self._state = STATE_IDLE
        self._auto = False

    def get_state(self):
        return self._state

    def trigger_automatic_update(self):
        if self._state == STATE_IDLE:
            _logger.debug("Starting automatic activity update")
            self.check_updates(True)

    def check_updates(self, auto=False):
        if self._state != STATE_IDLE:
            raise UpdaterStateException()

        self._auto = auto
        self._updates = []
        self._bundles_to_check = list(bundleregistry.get_registry())
        self._total_bundles_to_check = len(self._bundles_to_check)
        self._bundles_updated = []
        self._bundles_failed = []
        self._state = STATE_CHECKING
        self._check_next_update()

    def _check_next_update(self):
        total = self._total_bundles_to_check
        current = total - len(self._bundles_to_check)
        progress = current / float(total)

        if not self._bundles_to_check:
            self._finished_checking()
            return False

        bundle = self._bundles_to_check.pop()
        _logger.debug("Checking %s", bundle.get_bundle_id())
        self.emit('progress', self._state, bundle.get_name(), progress)

        aslo.fetch_update_info(bundle, self.__check_completed_cb)

    def _finished_checking(self):
        _logger.debug("_finished_checking")
        self._state = STATE_CHECKED
        if self._auto:
            self.update(None)
        else:
            self.emit('updates-available', self._updates)

    def __check_completed_cb(self, bundle, version, link, size, error_message):
        if error_message is not None:
            _logger.error('Error getting update information from server:\n'
                          '%s' % error_message)

        if version is not None and \
                version > NormalizedVersion(bundle.get_activity_version()):
            self._updates.append(BundleUpdate(bundle, version, link, size))

        if self._cancelling:
            self._finished(True)
        else:
            GLib.idle_add(self._check_next_update)

    def update(self, bundle_ids):
        if self._state != STATE_CHECKED:
            raise UpdaterStateException()

        if bundle_ids is None:
            self._bundles_to_update = self._updates
        else:
            self._bundles_to_update = []
            for bundle_update in self._updates:
                if bundle_update.bundle.get_bundle_id() in bundle_ids:
                    self._bundles_to_update.append(bundle_update)

        self._total_bundles_to_update = len(self._bundles_to_update)
        _logger.debug("Starting update of %d activities",
                      self._total_bundles_to_update)
        self._download_next_update()

    def _download_next_update(self):
        if self._cancelling:
            self._cancel_updating()
            return

        if len(self._bundles_to_update) == 0:
            self._finished()
            return

        self._state = STATE_DOWNLOADING
        self._bundle_update = self._bundles_to_update.pop()
        _logger.debug("Downloading update for %s",
                      self._bundle_update.bundle.get_bundle_id())

        total = self._total_bundles_to_update * 2
        current = total - len(self._bundles_to_update) * 2 - 2
        progress = current / float(total)

        self.emit('progress', self._state,
                  self._bundle_update.bundle.get_name(), progress)

        self._downloader = Downloader(self._bundle_update.link)
        self._downloader.connect('progress', self.__downloader_progress_cb)
        self._downloader.connect('error', self.__downloader_error_cb)
        self._downloader.connect('complete', self.__downloader_complete_cb)

    def __downloader_complete_cb(self, downloader):
        if self._cancelling:
            self._cancel_updating()
            return

        self._install_update(self._bundle_update,
                             self._downloader.get_local_file_path())
        self._downloader = None

    def __downloader_progress_cb(self, downloader, progress):
        if self._cancelling:
            self._cancel_updating()
            return

        total = self._total_bundles_to_update * 2
        current = total - len(self._bundles_to_update) * 2 - 2 + progress
        progress = current / float(total)

        self.emit('progress', self._state,
                  self._bundle_update.bundle.get_name(), progress)

    def __downloader_error_cb(self, downloader, error_message):
        _logger.error('Error downloading update:\n%s', error_message)
        self._bundles_failed.append(self._bundle_update)

        if self._cancelling:
            self._cancel_updating()
            return

        if self._bundles_to_update:
            self._download_next_update()

    def _install_update(self, bundle_update, local_file_path):
        self._state = STATE_UPDATING
        total = self._total_bundles_to_update
        current = total - len(self._bundles_to_update) - 0.5
        progress = current / float(total)

        _logger.debug("Installing update for %s",
                      bundle_update.bundle.get_bundle_id())
        self.emit('progress', self._state, bundle_update.bundle.get_name(),
                  progress)

        current += 0.5
        bundle = bundle_from_archive(local_file_path)
        registry = bundleregistry.get_registry()
        registry.install_async(bundle, self._bundle_installed_cb, current)

    def _bundle_installed_cb(self, bundle, result, progress):
        _logger.debug("%s installed: %r", bundle.get_bundle_id(), result)
        progress = progress / float(self._total_bundles_to_update)
        self.emit('progress', self._state, bundle.get_name(), progress)

        # Remove downloaded bundle archive
        try:
            os.unlink(bundle.get_path())
        except OSError:
            pass

        if result is True:
            self._bundles_updated.append(bundle)
        else:
            self._bundles_failed.append(bundle)

        # do it in idle so the UI has a chance to refresh
        GLib.idle_add(self._download_next_update)

    def _finished(self, cancelled=False):
        self._state = STATE_IDLE
        self._cancelling = False

        _logger.debug("Update finished")
        self.emit('finished', self._bundles_updated, self._bundles_failed,
                  cancelled)
        if not cancelled and len(self._bundles_failed) == 0:
            client = GConf.Client.get_default()
            client.set_int(_LAST_UPDATE_KEY, time.time())

    def cancel(self):
        self._cancelling = True

    def _cancel_updating(self):
        _logger.debug('Updater._cancel_updating')
        if self._downloader is not None:
            self._downloader.cancel()
            file_path = self._downloader.get_local_file_path()
            if file_path is not None and os.path.exists(file_path):
                os.unlink(file_path)
            self._downloader = None

        self._finished(True)


def get_instance():
    global _instance
    if _instance is None:
        _instance = Updater()
    return _instance


def _check_periodic_update():
    client = GConf.Client.get_default()
    update_frequency = client.get_int(_UPDATE_FREQUENCY_KEY)
    if update_frequency == 0:
        # automatic update disabled
        return False

    # convert update frequency from days to seconds
    update_frequency *= 24 * 60 * 60

    last_update = client.get_int(_LAST_UPDATE_KEY)
    now = time.time()
    _logger.debug("_check_periodic_update %r %r", last_update, now)
    if now - last_update > update_frequency:
        get_instance().trigger_automatic_update()

    return True


def startup_periodic_update():
    """
    Called a few minutes after Sugar starts.
    Checks to see if we have met the threshold where we should perform a
    periodic activity update. If so, perform an update.
    If automatic updates are enabled, the same check is then scheduled to
    run every 60 minutes.
    """

    if _check_periodic_update():
        GLib.timeout_add_seconds(3600, _check_periodic_update)
