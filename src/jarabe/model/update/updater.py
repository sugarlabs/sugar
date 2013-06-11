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

from gi.repository import GObject
from gi.repository import GLib

from sugar3.bundle import bundle_from_archive
from sugar3.bundle.bundleversion import NormalizedVersion

from jarabe.model import bundleregistry
from jarabe.util.downloader import Downloader

from jarabe.model.update import BundleUpdate, aslo


class Updater(GObject.GObject):
    __gtype_name__ = 'SugarUpdater'

    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ([int, str, float, int])),
    }

    ACTION_CHECKING = 0
    ACTION_UPDATING = 1
    ACTION_DOWNLOADING = 2

    def __init__(self):
        GObject.GObject.__init__(self)

        self.updates = None
        self._bundles_to_check = None
        self._bundles_to_update = None
        self._total_bundles_to_update = 0
        self._bundle_update = None
        self._downloader = None
        self._cancelling = False

    def check_updates(self):
        self.updates = []
        self._bundles_to_check = list(bundleregistry.get_registry())
        self._check_next_update()

    def _check_next_update(self):
        total = len(bundleregistry.get_registry())
        current = total - len(self._bundles_to_check)

        if not self._bundles_to_check:
            return False

        bundle = self._bundles_to_check.pop()
        self.emit('progress', Updater.ACTION_CHECKING, bundle.get_name(),
                  current, total)

        aslo.fetch_update_info(bundle, self.__check_completed_cb)

    def __check_completed_cb(self, bundle, version, link, size, error_message):
        if error_message is not None:
            logging.error('Error getting update information from server:\n'
                          '%s' % error_message)

        if version is not None and \
                version > NormalizedVersion(bundle.get_activity_version()):
            self.updates.append(BundleUpdate(bundle, version, link, size))

        if self._cancelling:
            self._cancel_checking()
        elif self._bundles_to_check:
            GLib.idle_add(self._check_next_update)
        else:
            total = len(bundleregistry.get_registry())
            if bundle is None:
                name = ''
            else:
                name = bundle.get_name()
            self.emit('progress', Updater.ACTION_CHECKING, name, total,
                      total)

    def update(self, bundle_ids):
        self._bundles_to_update = []
        for bundle_update in self.updates:
            if bundle_update.bundle.get_bundle_id() in bundle_ids:
                self._bundles_to_update.append(bundle_update)

        self._total_bundles_to_update = len(self._bundles_to_update)
        self._download_next_update()

    def _download_next_update(self):
        if self._cancelling:
            self._cancel_updating()
            return

        self._bundle_update = self._bundles_to_update.pop()

        total = self._total_bundles_to_update * 2
        current = total - len(self._bundles_to_update) * 2 - 2

        self.emit('progress', Updater.ACTION_DOWNLOADING,
                  self._bundle_update.bundle.get_name(), current, total)

        self._downloader = Downloader(self._bundle_update.link)
        self._downloader.connect('progress', self.__downloader_progress_cb)
        self._downloader.connect('error', self.__downloader_error_cb)
        self._downloader.connect('complete', self.__downloader_complete_cb)

    def __downloader_complete_cb(self, downloader):
        self._install_update(self._bundle_update,
                             self._downloader.get_local_file_path())
        self._downloader = None

    def __downloader_progress_cb(self, downloader, progress):
        logging.debug('__downloader_progress_cb %r', progress)

        if self._cancelling:
            self._cancel_updating()
            return

        total = self._total_bundles_to_update * 2
        current = total - len(self._bundles_to_update) * 2 - 2 + progress

        self.emit('progress', Updater.ACTION_DOWNLOADING,
                  self._bundle_update.bundle.get_name(),
                  current, total)

    def __downloader_error_cb(self, downloader, error_message):
        logging.error('Error downloading update:\n%s', error_message)

        if self._cancelling:
            self._cancel_updating()
            return

        total = self._total_bundles_to_update
        current = total - len(self._bundles_to_update)
        self.emit('progress', Updater.ACTION_UPDATING, '', current, total)

        if self._bundles_to_update:
            # do it in idle so the UI has a chance to refresh
            GLib.idle_add(self._download_next_update)

    def _install_update(self, bundle_update, local_file_path):

        total = self._total_bundles_to_update
        current = total - len(self._bundles_to_update) - 0.5

        self.emit('progress', Updater.ACTION_UPDATING,
                  bundle_update.bundle.get_name(),
                  current, total)

        current += 0.5
        bundle = bundle_from_archive(local_file_path)
        registry = bundleregistry.get_registry()
        registry.install_async(bundle, self._bundle_installed_cb, current)

    def _bundle_installed_cb(self, bundle, result, progress):
        logging.debug("%s installed: %r", bundle.get_bundle_id(), result)
        self.emit('progress', Updater.ACTION_UPDATING,
                  bundle.get_name(), progress, self._total_bundles_to_update)

        # Remove downloaded bundle archive
        try:
            os.unlink(bundle.get_path())
        except OSError:
            pass

        if self._bundles_to_update:
            # do it in idle so the UI has a chance to refresh
            GLib.idle_add(self._download_next_update)

    def cancel(self):
        self._cancelling = True

    def _cancel_checking(self):
        logging.debug('Updater._cancel_checking')
        total = len(bundleregistry.get_registry())
        current = total - len(self._bundles_to_check)
        self.emit('progress', Updater.ACTION_CHECKING, '', current,
                  current)
        self._bundles_to_check = None
        self._cancelling = False

    def _cancel_updating(self):
        logging.debug('Updater._cancel_updating')
        current = (self._total_bundles_to_update -
                   len(self._bundles_to_update) - 1)
        self.emit('progress', Updater.ACTION_UPDATING, '', current,
                  current)

        if self._downloader is not None:
            self._downloader.cancel()
            file_path = self._downloader.get_local_file_path()
            if file_path is not None and os.path.exists(file_path):
                os.unlink(file_path)
            self._downloader = None

        self._total_bundles_to_update = 0
        self._bundles_to_update = None
        self._cancelling = False
