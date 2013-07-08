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
from urlparse import urlparse
import tempfile

from gi.repository import GObject
from gi.repository import Soup
from gi.repository import Gio

from jarabe import config
from sugar3 import env

_session = None

SOUP_STATUS_CANCELLED = 1


def soup_status_is_successful(status):
    return status >= 200 and status < 300


def get_soup_session():
    global _session
    if _session is None:
        _session = Soup.SessionAsync()
        _session.set_property("timeout", 60)
        _session.set_property("idle-timeout", 60)
        _session.set_property("user-agent", "Sugar/%s" % config.version)
    return _session


class Downloader(GObject.GObject):
    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ([float])),
        'complete': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     (object,)),
    }

    def __init__(self, url, session=None):
        GObject.GObject.__init__(self)
        temp_file_path = self._get_temp_file_path(url)
        url = Soup.URI.new(url)
        self._session = session or get_soup_session()
        self._pending_buffers = []
        self._downloaded_size = 0
        self._total_size = 0
        self._cancelling = False
        self._status_code = None

        self._output_file = Gio.File.new_for_path(temp_file_path)
        self._output_stream = self._output_file.create(
            Gio.FileCreateFlags.PRIVATE, None)

        self._message = Soup.Message(method="GET", uri=url)
        self._message.connect('got-chunk', self._got_chunk_cb)
        self._message.connect('got-headers', self._headers_cb, None)
        self._message.request_body.set_accumulate(False)

    def run(self):
        self._session.queue_message(self._message, self._message_cb, None)

    def _message_cb(self, session, message, user_data):
        self._status_code = message.status_code
        self._check_if_finished()

    def cancel(self):
        self._cancelling = True
        self._session.cancel_message(self._message, SOUP_STATUS_CANCELLED)

    def _headers_cb(self, message, user_data):
        if soup_status_is_successful(message.status_code):
            self._total_size = message.response_headers.get_content_length()

    def _got_chunk_cb(self, message, buf):
        if self._cancelling or \
                not soup_status_is_successful(message.status_code):
            return

        self._pending_buffers.append(buf.get_as_bytes())
        self._write_next_buffer()

    def __write_async_cb(self, output_stream, result, user_data):
        count = output_stream.write_bytes_finish(result)

        self._downloaded_size += count
        if self._total_size > 0:
            progress = self._downloaded_size / float(self._total_size)
            self.emit('progress', progress)

        self._check_if_finished()

    def _complete(self):
        error = None
        if not soup_status_is_successful(self._status_code):
            error = IOError("HTTP error code %d" % self._status_code)
        self._output_stream.close(None)
        self.emit('complete', error)

    def _check_if_finished(self):
        # To finish (for both successful completion and cancellation), we
        # require two conditions to become true:
        #  1. Soup message callback has been called
        #  2. Any pending output file write completes
        # Those conditions can become true in either order.
        if self._cancelling or not self._pending_buffers:
            if self._status_code is not None \
                    and not self._output_stream.has_pending():
                self._complete()
            return

        self._write_next_buffer()

    def _write_next_buffer(self):
        if not self._output_stream.has_pending():
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
