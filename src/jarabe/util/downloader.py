# Copyright (C) 2009-2013, Sugar Labs
# Copyright (C) 2009, Tomeu Vizoso
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


import os
from urlparse import urlparse
import tempfile

import gi
gi.require_version('Soup', '2.4')
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
        _session.add_feature_by_type(Soup.ProxyResolverDefault)
    return _session


class Downloader(GObject.GObject):
    __gsignals__ = {
        'progress': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     ([float])),
        'got-chunk': (GObject.SignalFlags.RUN_FIRST,
                      None,
                      (object,)),
        'complete': (GObject.SignalFlags.RUN_FIRST,
                     None,
                     (object,)),
    }

    def __init__(self, url, session=None, request_headers=None):
        GObject.GObject.__init__(self)
        self._uri = Soup.URI.new(url)
        self._session = session or get_soup_session()
        self._pending_buffers = []
        self._downloaded_size = 0
        self._total_size = 0
        self._cancelling = False
        self._status_code = None
        self._output_file = None
        self._output_stream = None
        self._message = None
        self._request_headers = request_headers

    def _setup_message(self, method="GET"):
        self._message = Soup.Message(method=method, uri=self._uri)
        self._message.connect('got-chunk', self._got_chunk_cb)
        self._message.connect('got-headers', self._headers_cb, None)
        if self._request_headers is not None:
            for header_key in self._request_headers.keys():
                self._message.request_headers.append(
                    header_key, self._request_headers[header_key])

    def download_to_temp(self):
        """
        Download the contents of the provided URL to temporary file storage.
        Use .get_local_file_path() to find the location of where the file
        is saved. Upon completion, a successful download is indicated by a
        result of None in the complete signal parameters.
        """
        url = self._uri.to_string(False)
        temp_file_path = self._get_temp_file_path(url)
        self._output_file = Gio.File.new_for_path(temp_file_path)
        self._output_stream = self._output_file.create(
            Gio.FileCreateFlags.PRIVATE, None)
        self.download_chunked()

    def download_chunked(self):
        """
        Download the contents of the provided URL into memory. The download
        is done in chunks, and each chunk is emitted over the 'got-chunk'
        signal. Upon completion, a successful download is indicated by a
        reuslt of None in the complete signal parameters.
        """
        self._setup_message()
        self._message.response_body.set_accumulate(False)
        self._session.queue_message(self._message, self._message_cb, None)

    def download(self, start=None, end=None):
        """
        Download the contents of the provided URL into memory.
        Upon completion, the downloaded data will be passed as GBytes to the
        result parameter of the complete signal handler.
        The start and end parameters can optionally be set to perform a
        partial read of the remote data.
        """
        self._setup_message()
        if start is not None:
            self._message.request_headers.set_range(start, end)
        self._session.queue_message(self._message, self._message_cb, None)

    def get_size(self):
        """
        Perform a HTTP HEAD request to find the size of the remote content.
        The size is returned in the result parameter of the 'complete' signal.
        """
        self._setup_message("HEAD")
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

        data = buf.get_as_bytes()
        self.emit('got-chunk', data)
        if self._output_stream:
            self._pending_buffers.append(data)
            self._write_next_buffer()

    def __write_async_cb(self, output_stream, result, user_data):
        count = output_stream.write_bytes_finish(result)

        self._downloaded_size += count
        if self._total_size > 0:
            progress = self._downloaded_size / float(self._total_size)
            self.emit('progress', progress)

        self._check_if_finished()

    def _complete(self):
        if self._output_stream:
            self._output_stream.close(None)

        result = None
        if soup_status_is_successful(self._status_code):
            if self._message.method == "HEAD":
                # this is a get_size request
                result = self._total_size
            elif self._message.response_body.get_accumulate():
                # the message body must be flattened so that it can be
                # retrieved as GBytes because response_body.data gets
                # incorrectly treated by introspection as a NULL-terminated
                # string
                # https://bugzilla.gnome.org/show_bug.cgi?id=704105
                result = self._message.response_body.flatten().get_as_bytes()
        else:
            result = IOError("HTTP error code %d" % self._status_code)
        self.emit('complete', result)

    def _check_if_finished(self):
        # To finish (for both successful completion and cancellation), we
        # require two conditions to become true:
        #  1. Soup message callback has been called
        #  2. Any pending output file write completes
        # Those conditions can become true in either order.
        if not self._output_stream:
            self._complete()
            return

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
        if self._output_file:
            return self._output_file.get_path()
