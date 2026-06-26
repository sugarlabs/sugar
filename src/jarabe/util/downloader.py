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
from urllib.parse import urlparse
import tempfile

import gi
gi.require_version('Soup', '3.0')
from gi.repository import GObject
from gi.repository import Soup
from gi.repository import Gio
from gi.repository import GLib

from jarabe import config
from sugar4 import env

_session = None

SOUP_STATUS_CANCELLED = 1


def soup_status_is_successful(status):
    return status >= 200 and status < 300


def get_soup_session():
    global _session
    if _session is None:
        _session = Soup.Session()
        _session.props.timeout = 60
        _session.props.idle_timeout = 60
        _session.props.user_agent = "Sugar/%s" % config.version
        _session.props.proxy_resolver = Gio.ProxyResolver.get_default()
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
        super().__init__()
        self._uri = GLib.Uri.parse(url, GLib.UriFlags.NONE)
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
        self._cancellable = Gio.Cancellable()
        self._read_finished = False
        self._accumulated_data = bytearray()
        self._is_chunked = False

    def _setup_message(self, method="GET"):
        self._message = Soup.Message.new(method, self._uri.to_string())
        if self._request_headers is not None:
            for header_key in list(self._request_headers.keys()):
                self._message.get_request_headers().append(
                    header_key, self._request_headers[header_key])

    def download_to_temp(self):
        """
        Download the contents of the provided URL to temporary file storage.
        Use .get_local_file_path() to find the location of where the file
        is saved. Upon completion, a successful download is indicated by a
        result of None in the complete signal parameters.
        """
        url = self._uri.to_string()
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
        self._is_chunked = True
        self._setup_message()
        self._session.send_async(self._message, GLib.PRIORITY_DEFAULT, self._cancellable, self._message_cb, None)

    def download(self, start=None, end=None):
        """
        Download the contents of the provided URL into memory.
        Upon completion, the downloaded data will be passed as GBytes to the
        result parameter of the complete signal handler.
        The start and end parameters can optionally be set to perform a
        partial read of the remote data.
        """
        self._is_chunked = False
        self._setup_message()
        if start is not None:
            self._message.get_request_headers().set_range(start, end)
        self._session.send_async(self._message, GLib.PRIORITY_DEFAULT, self._cancellable, self._message_cb, None)

    def get_size(self):
        """
        Perform a HTTP HEAD request to find the size of the remote content.
        The size is returned in the result parameter of the 'complete' signal.
        """
        self._setup_message("HEAD")
        self._session.send_async(self._message, GLib.PRIORITY_DEFAULT, self._cancellable, self._message_cb, None)

    def _message_cb(self, session, res, user_data):
        try:
            stream = session.send_finish(res)
            self._status_code = self._message.get_status()
            if soup_status_is_successful(self._status_code):
                self._total_size = self._message.get_response_headers().get_content_length()

            if self._message.get_method() == "HEAD":
                self._read_finished = True
                self._check_if_finished()
            else:
                self._read_next_chunk(stream)
        except Exception:
            self._status_code = self._message.get_status()
            if self._status_code == 0:
                self._status_code = SOUP_STATUS_CANCELLED
            self._read_finished = True
            self._check_if_finished()

    def _read_next_chunk(self, stream):
        if self._cancelling or not soup_status_is_successful(self._status_code):
            self._read_finished = True
            self._check_if_finished()
            return
        stream.read_bytes_async(8192, GLib.PRIORITY_DEFAULT, self._cancellable, self._read_cb, stream)

    def _read_cb(self, stream, res, user_data):
        if self._cancelling:
            self._read_finished = True
            self._check_if_finished()
            return

        try:
            data = stream.read_bytes_finish(res)
        except Exception:
            self._status_code = SOUP_STATUS_CANCELLED
            self._read_finished = True
            self._check_if_finished()
            return

        if data is None or data.get_size() == 0:
            self._read_finished = True
            self._check_if_finished()
            return

        self.emit('got-chunk', data)

        if not self._is_chunked and not self._output_stream:
            self._accumulated_data.extend(data.get_data())

        if self._output_stream:
            self._pending_buffers.append(data)
            self._write_next_buffer()
        else:
            self._downloaded_size += data.get_size()
            if self._total_size > 0:
                progress = self._downloaded_size / float(self._total_size)
                self.emit('progress', progress)

        self._read_next_chunk(stream)

    def cancel(self):
        self._cancelling = True
        self._cancellable.cancel()

    def __write_async_cb(self, output_stream, result, user_data):
        try:
            count = output_stream.write_bytes_finish(result)
            self._downloaded_size += count
            if self._total_size > 0:
                progress = self._downloaded_size / float(self._total_size)
                self.emit('progress', progress)
        except Exception:
            self._status_code = SOUP_STATUS_CANCELLED
            self.cancel()

        self._check_if_finished()

    def _complete(self):
        if self._output_stream:
            try:
                self._output_stream.close(None)
            except Exception:
                pass
            self._output_stream = None

        result = None
        if soup_status_is_successful(self._status_code):
            if self._message.get_method() == "HEAD":
                # this is a get_size request
                result = self._total_size
            elif not self._is_chunked and self._output_file is None:
                result = GLib.Bytes.new(bytes(self._accumulated_data))
        else:
            result = IOError("HTTP error code %d" % self._status_code)
        self.emit('complete', result)

    def _check_if_finished(self):
        # To finish (for both successful completion and cancellation), we
        # require two conditions to become true:
        #  1. Soup message callback has been called and stream fully read
        #  2. Any pending output file write completes
        # Those conditions can become true in either order.
        if not self._output_stream:
            if self._read_finished:
                self._complete()
            return

        if self._cancelling or not self._pending_buffers:
            if self._read_finished and not self._output_stream.has_pending():
                self._complete()
            return

        self._write_next_buffer()

    def _write_next_buffer(self):
        if self._output_stream and not self._output_stream.has_pending() and self._pending_buffers:
            data = self._pending_buffers.pop(0)
            self._output_stream.write_bytes_async(data, GLib.PRIORITY_LOW,
                                                  self._cancellable, self.__write_async_cb,
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
