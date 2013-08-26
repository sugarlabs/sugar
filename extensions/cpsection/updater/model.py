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
"""Sugar bundle updater: model.

This module implements the non-GUI portions of the bundle updater, including
list of installed bundls, whether updates are needed, and the URL at which to
find the bundle updated.
"""

import os
import logging
import tempfile
from urlparse import urlparse
import traceback

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib

from sugar3 import env
from sugar3.datastore import datastore
from sugar3.bundle.activitybundle import ActivityBundle
from sugar3.bundle.bundleversion import NormalizedVersion

from jarabe.model import bundleregistry

from backends import aslo


class UpdateModel(GObject.GObject):
    __gtype_name__ = 'SugarUpdateModel'

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
        self.emit('progress', UpdateModel.ACTION_CHECKING, bundle.get_name(),
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
            self.emit('progress', UpdateModel.ACTION_CHECKING, name, total,
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

        bundle_update = self._bundles_to_update.pop()

        total = self._total_bundles_to_update * 2
        current = total - len(self._bundles_to_update) * 2 - 2

        self.emit('progress', UpdateModel.ACTION_DOWNLOADING,
                  bundle_update.bundle.get_name(), current, total)

        self._downloader = _Downloader(bundle_update)
        self._downloader.connect('progress', self.__downloader_progress_cb)
        self._downloader.connect('error', self.__downloader_error_cb)

    def __downloader_progress_cb(self, downloader, progress):
        logging.debug('__downloader_progress_cb %r', progress)

        if self._cancelling:
            self._cancel_updating()
            return

        total = self._total_bundles_to_update * 2
        current = total - len(self._bundles_to_update) * 2 - 2 + progress

        self.emit('progress', UpdateModel.ACTION_DOWNLOADING,
                  self._downloader.bundle_update.bundle.get_name(),
                  current, total)

        if progress == 1:
            self._install_update(self._downloader.bundle_update,
                                 self._downloader.get_local_file_path())
            self._downloader = None

    def __downloader_error_cb(self, downloader, error_message):
        logging.error('Error downloading update:\n%s', error_message)

        if self._cancelling:
            self._cancel_updating()
            return

        total = self._total_bundles_to_update
        current = total - len(self._bundles_to_update)
        self.emit('progress', UpdateModel.ACTION_UPDATING, '', current, total)

        if self._bundles_to_update:
            # do it in idle so the UI has a chance to refresh
            GLib.idle_add(self._download_next_update)

    def _install_update(self, bundle_update, local_file_path):

        total = self._total_bundles_to_update
        current = total - len(self._bundles_to_update) - 0.5

        self.emit('progress', UpdateModel.ACTION_UPDATING,
                  bundle_update.bundle.get_name(),
                  current, total)

        # TODO: Should we first expand the zip async so we can provide progress
        # and only then copy to the journal?
        jobject = datastore.create()
        try:
            title = '%s-%s' % (bundle_update.bundle.get_name(),
                               bundle_update.version)
            jobject.metadata['title'] = title
            jobject.metadata['mime_type'] = ActivityBundle.MIME_TYPE
            jobject.file_path = local_file_path
            datastore.write(jobject, transfer_ownership=True)
        finally:
            jobject.destroy()

        self.emit('progress', UpdateModel.ACTION_UPDATING,
                  bundle_update.bundle.get_name(),
                  current + 0.5, total)

        if self._bundles_to_update:
            # do it in idle so the UI has a chance to refresh
            GLib.idle_add(self._download_next_update)

    def cancel(self):
        self._cancelling = True

    def _cancel_checking(self):
        logging.debug('UpdateModel._cancel_checking')
        total = len(bundleregistry.get_registry())
        current = total - len(self._bundles_to_check)
        self.emit('progress', UpdateModel.ACTION_CHECKING, '', current,
                  current)
        self._bundles_to_check = None
        self._cancelling = False

    def _cancel_updating(self):
        logging.debug('UpdateModel._cancel_updating')
        current = (self._total_bundles_to_update -
                   len(self._bundles_to_update) - 1)
        self.emit('progress', UpdateModel.ACTION_UPDATING, '', current,
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


class BundleUpdate(object):

    def __init__(self, bundle, version, link, size):
        self.bundle = bundle
        self.version = version
        self.link = link
        self.size = size


class _Downloader(GObject.GObject):
    _CHUNK_SIZE = 10240  # 10K
    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ([float])),
        'error': (GObject.SignalFlags.RUN_FIRST,
                  None,
                  ([str])),
    }

    def __init__(self, bundle_update):
        GObject.GObject.__init__(self)

        self.bundle_update = bundle_update
        self._input_stream = None
        self._output_stream = None
        self._pending_buffers = []
        self._input_file = Gio.File.new_for_uri(bundle_update.link)
        self._output_file = None
        self._downloaded_size = 0
        self._cancelling = False

        self._input_file.read_async(GLib.PRIORITY_DEFAULT, None,
                              self.__file_read_async_cb, None)

    def cancel(self):
        self._cancelling = True

    def __file_read_async_cb(self, gfile, result, user_data):
        if self._cancelling:
            return

        try:
            self._input_stream = self._input_file.read_finish(result)
        except:
            self.emit('error', traceback.format_exc())
            return

        temp_file_path = self._get_temp_file_path(self.bundle_update.link)
        self._output_file = Gio.File.new_for_path(temp_file_path)
        self._output_stream = self._output_file.create(
            Gio.FileCreateFlags.PRIVATE, None)
        self._input_stream.read_bytes_async(
            self._CHUNK_SIZE, GLib.PRIORITY_DEFAULT, None,
            self.__stream_read_async_cb, None)

    def __stream_read_async_cb(self, input_stream, result, user_data):
        if self._cancelling:
            return

        data = input_stream.read_bytes_finish(result)

        if data is None:
            # TODO
            pass
        elif data.get_size() == 0:
            logging.debug('closing input stream')
            input_stream.close(None)
            self._check_if_finished_writing()
        else:
            self._pending_buffers.append(data)
            input_stream.read_bytes_async(self._CHUNK_SIZE,
                                          GLib.PRIORITY_DEFAULT, None,
                                          self.__stream_read_async_cb, None)

        self._write_next_buffer()

    def __write_async_cb(self, output_stream, result, user_data):
        if self._cancelling:
            return

        count = output_stream.write_bytes_finish(result)

        self._downloaded_size += count
        progress = self._downloaded_size / float(self.bundle_update.size)
        self.emit('progress', progress)

        self._check_if_finished_writing()

        if self._pending_buffers:
            self._write_next_buffer()

    def _write_next_buffer(self):
        if self._pending_buffers and not self._output_stream.has_pending():
            data = self._pending_buffers.pop(0)
            self._output_stream.write_bytes_async(data, GObject.PRIORITY_LOW,
                                                  None, self.__write_async_cb,
                                                  None)

    def _get_temp_file_path(self, uri):
        # TODO: Should we use the HTTP headers for the file name?
        scheme_, netloc_, path, params_, query_, fragment_ = \
                urlparse(uri)
        path = os.path.basename(path)

        if not os.path.exists(env.get_user_activities_path()):
            os.makedirs(env.get_user_activities_path())

        base_name, extension_ = os.path.splitext(path)
        fd, file_path = tempfile.mkstemp(dir=env.get_user_activities_path(),
                prefix=base_name, suffix='.xo')
        os.close(fd)
        os.unlink(file_path)

        return file_path

    def get_local_file_path(self):
        return self._output_file.get_path()

    def _check_if_finished_writing(self):
        if not self._pending_buffers and \
                not self._output_stream.has_pending() and \
                self._input_stream.is_closed():

            logging.debug('closing output stream')
            self._output_stream.close(None)

            self.emit('progress', 1.0)
