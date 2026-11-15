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
from sugar3 import env

_session = None

CHUNK_SIZE = 64 * 1024


def soup_status_is_successful(status):
    return 200 <= status < 300


def get_soup_session():
    global _session
    if _session is None:
        _session = Soup.Session()
        _session.set_timeout(60)
        _session.set_idle_timeout(60)
        _session.set_user_agent("Sugar/%s" % config.version)
        _session.set_proxy_resolver(Gio.ProxyResolver.get_default())
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
        self._uri = GLib.Uri.parse(url, GLib.UriFlags.NONE)
        self._session = session or get_soup_session()
        self._chunks = []
        self._downloaded_size = 0
        self._total_size = 0
        self._cancelling = False
        self._cancellable = Gio.Cancellable()
        self._input_stream = None
        self._completed = False
        self._error = None
        self._status_code = None
        self._output_file = None
        self._output_stream = None
        self._message = None
        self._request_headers = request_headers

    def _setup_message(self, method="GET"):
        self._message = Soup.Message.new_from_uri(method, self._uri)

        if self._request_headers is not None:
            for header_key in self._request_headers:
                self._message.get_request_headers().append(
                    header_key, self._request_headers[header_key])

    def download_to_temp(self):
        """
        Download the contents of the provided URL to temporary file storage.
        Use get_local_file_path() to find the location of the saved file.
        Upon completion, a successful download is indicated by a result of
        None in the complete signal parameters.
        """
        url = self._uri.to_string()
        temp_file_path = self._get_temp_file_path(url)
        self._output_file = Gio.File.new_for_path(temp_file_path)
        self._output_stream = self._output_file.create(
            Gio.FileCreateFlags.PRIVATE, None)
        self.download_chunked()

    def download_chunked(self):
        """
        Download the contents of the provided URL into memory.
        The download is done in chunks, and each chunk is emitted over the
        got-chunk signal. Upon completion, a successful download is indicated
        by a result of None in the complete signal parameters.
        """
        self._setup_message()
        self._session.send_async(
            self._message, GLib.PRIORITY_DEFAULT,
            self._cancellable, self._message_cb, None)

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
            self._message.get_request_headers().set_range(start, end)

        self._session.send_async(
            self._message, GLib.PRIORITY_DEFAULT,
            self._cancellable, self._message_cb, None)

    def get_size(self):
        """
        Perform a HTTP HEAD request to find the size of the remote content.
        The size is returned in the result parameter of the complete signal.
        """
        self._setup_message("HEAD")
        self._session.send_async(
            self._message, GLib.PRIORITY_DEFAULT,
            self._cancellable, self._message_cb, None)

    def _message_cb(self, session, result, user_data):
        try:
            self._input_stream = session.send_finish(result)
        except GLib.Error as error:
            self._error = error
            self._status_code = self._message.get_status()
            self._complete()
            return

        self._status_code = self._message.get_status()

        if not soup_status_is_successful(self._status_code):
            self._complete()
            return

        self._total_size = (
            self._message.get_response_headers().get_content_length())

        if self._message.get_method() == "HEAD":
            self._complete()
            return

        self._read_next_chunk()

    def cancel(self):
        self._cancelling = True
        self._cancellable.cancel()

    def __write_async_cb(self, output_stream, result, user_data):
        try:
            success, count = output_stream.write_all_finish(result)
        except GLib.Error as error:
            self._error = error
            self._complete()
            return

        if not success:
            self._error = IOError("Failed to write downloaded data")
            self._complete()
            return

        self._downloaded_size += count
        self._emit_progress()
        self._read_next_chunk()

    def _read_next_chunk(self):
        if self._completed:
            return

        self._input_stream.read_bytes_async(
            CHUNK_SIZE,
            GLib.PRIORITY_DEFAULT,
            self._cancellable,
            self._read_async_cb,
            None)

    def _read_async_cb(self, input_stream, result, user_data):
        try:
            data = input_stream.read_bytes_finish(result)
        except GLib.Error as error:
            self._error = error
            self._complete()
            return

        if data.get_size() == 0:
            self._complete()
            return

        self.emit('got-chunk', data)

        if self._output_stream:
            self._output_stream.write_all_async(
                data.get_data(),
                GLib.PRIORITY_LOW,
                self._cancellable,
                self.__write_async_cb,
                None)
        else:
            self._chunks.append(data)
            self._downloaded_size += data.get_size()
            self._emit_progress()
            self._read_next_chunk()

    def _emit_progress(self):
        if self._total_size > 0:
            progress = self._downloaded_size / float(self._total_size)
            self.emit('progress', progress)

    def _complete(self):
        if self._completed:
            return

        self._completed = True

        if self._input_stream:
            try:
                self._input_stream.close(None)
            except GLib.Error:
                pass

        if self._output_stream:
            try:
                self._output_stream.close(None)
            except GLib.Error as error:
                if self._error is None:
                    self._error = error

        if self._error is not None:
            result = self._error
        elif not soup_status_is_successful(self._status_code):
            result = IOError("HTTP error code %d" % self._status_code)
        elif self._message.get_method() == "HEAD":
            result = self._total_size
        elif self._output_stream:
            result = None
        else:
            result = GLib.Bytes.new(
                b''.join(chunk.get_data() for chunk in self._chunks))

        self.emit('complete', result)

    def _get_temp_file_path(self, uri):
        # TODO: Should we use the HTTP headers for the file name?
        scheme_, netloc_, path, params_, query_, fragment_ = \
            urlparse(uri)
        path = os.path.basename(path)

        tmp_dir = os.path.join(env.get_profile_path(), 'data')
        base_name, extension_ = os.path.splitext(path)
        fd, file_path = tempfile.mkstemp(
            dir=tmp_dir, prefix=base_name, suffix=extension_)
        os.close(fd)
        os.unlink(file_path)

        return file_path

    def get_local_file_path(self):
        if self._output_file:
            return self._output_file.get_path()
