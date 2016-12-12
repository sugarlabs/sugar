# Copyright (C) 2014 Sam Parkinson
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import json
import logging

from sugar3.bundle.bundleversion import NormalizedVersion, InvalidVersionError
from gi.repository import Gio

from jarabe.model.update import BundleUpdate
from jarabe.util.downloader import Downloader
from jarabe import config


class NewAsloUpdater(object):
    """
    Checks for updates using the new ASLO's update.json file
    """

    def __init__(self):
        self._completion_cb = None
        self._progress_cb = None
        self._error_cb = None

        self._bundles = []
        self._downloader = None
        self._canceled = False

    def fetch_update_info(self, installed_bundles, auto, progress_cb,
                          completion_cb, error_cb):
        self._completion_cb = completion_cb
        self._progress_cb = progress_cb
        self._error_cb = error_cb

        self._bundles = installed_bundles

        self._progress_cb('', 0)  # Set the status to 'Looking for updates'

        settings = Gio.Settings('org.sugarlabs.update')
        data_json_url = settings.get_string('new-aslo-url')
        self._downloader = Downloader(data_json_url)
        self._downloader.connect('complete',
                                 self.__data_json_download_complete_cb)
        self._downloader.download()

    def __data_json_download_complete_cb(self, downloader, result):
        if self._canceled:
            return

        try:
            activities = json.loads(result.get_data())['activities']
        except ValueError:
            self._error_cb('Can not parse loaded update.json')
            return

        updates = []

        for i, bundle in enumerate(self._bundles):
            self._progress_cb(bundle.get_name(), i / len(self._bundles))

            if bundle.get_bundle_id() not in activities:
                logging.debug('%s not in activities' % bundle.get_bundle_id())
                continue
            activity = activities[bundle.get_bundle_id()]

            try:
                version = NormalizedVersion(str(activity['version']))
                min_sugar = NormalizedVersion(str(activity['minSugarVersion']))
            except KeyError:
                logging.debug('KeyError - %s' % bundle.get_bundle_id())
                continue
            except InvalidVersionError:
                logging.debug('InvalidVersion - %s' % bundle.get_bundle_id())
                continue

            if NormalizedVersion(bundle.get_activity_version()) >= version:
                logging.debug('%s is up to date' % bundle.get_bundle_id())
                continue

            if NormalizedVersion(config.version) < min_sugar:
                logging.debug('Upgrade sugar for %s' % bundle.get_bundle_id())
                continue

            logging.debug('Marked for update: %s' % bundle.get_bundle_id())
            u = BundleUpdate(bundle.get_bundle_id(), bundle.get_name(),
                             version,
                             activity['xo_url'],
                             activity.get('xo_size', 1024 * 2))
            updates.append(u)

        self._completion_cb(updates)

    def cancel(self):
        self._canceled = True

        if self._downloader:
            self._downloader.cancel()
            self._completion_cb(None)

    def clean(self):
        self._canceled = False
