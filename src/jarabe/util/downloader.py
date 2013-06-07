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
from urlparse import urlparse
import tempfile
import traceback

from gi.repository import GObject
from gi.repository import Gio
from gi.repository import GLib

from sugar3 import env


class Downloader(GObject.GObject):
    _CHUNK_SIZE = 10240  # 10K
    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ([float])),
        'complete': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ([])),
        'error': (GObject.SignalFlags.RUN_FIRST,
                  None,
                  ([str])),
    }

    def __init__(self, url):
        GObject.GObject.__init__(self)

        self._input_stream = None
        self._output_stream = None
        self._pending_buffers = []
        self._input_file = Gio.File.new_for_uri(url)
        self._output_file = None
        self._downloaded_size = 0
        self._total_size = 0
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

        info = self._input_stream.query_info(Gio.FILE_ATTRIBUTE_STANDARD_SIZE,
                                             None)
        self._total_size = info.get_size()

        temp_file_path = self._get_temp_file_path(self._input_file.get_uri())
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
        progress = self._downloaded_size / float(self._total_size)
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

        tmp_dir = os.path.join(env.get_profile_path(), 'data')
        base_name, extension_ = os.path.splitext(path)
        fd, file_path = tempfile.mkstemp(dir=tmp_dir,
                                         prefix=base_name, suffix=extension_)
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

            self.emit('complete')
