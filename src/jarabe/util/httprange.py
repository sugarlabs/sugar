# Copyright (C) 2008-2013 One Laptop per Child
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


"""
A simple HTTP-based file-like object that supports seek() via the HTTP
Range header. This means it doesn't have to download the whole file just
to read a small part of it. Uses Downloader as a backend, and runs the
regular main loop while waiting for data.
"""

from gi.repository import Gtk

from jarabe.util.downloader import Downloader


class _HttpRangeFileObject(object):

    def __init__(self, url):
        self._url = url
        self._size = None
        self._offset = 0
        self._result = None
        self._complete = False

    def _downloader_complete_cb(self, downloader, result):
        self._result = result
        self._complete = True

    def _do_download(self, method, **kwargs):
        # set up Downloader, call method on it with given kwargs, wait for
        # response
        self._complete = False
        downloader = Downloader(self._url)
        downloader.connect('complete', self._downloader_complete_cb)
        getattr(downloader, method)(**kwargs)

        while not self._complete:
            Gtk.main_iteration()

        if isinstance(self._result, Exception):
            raise self._result

    def tell(self):
        return self._offset

    def size(self):
        if self._size is None:
            self._do_download('get_size')
            if self._result is None:
                raise IOError("No content length header")
            self._size = self._result
        return self._size

    def read(self, size=-1):
        if size < 0:
            end = self.size()
        else:
            end = self._offset + size

        self._complete = False

        self._do_download('download', start=self._offset, end=end - 1)
        data = self._result.get_data()
        self._offset += len(data)
        return data

    def seek(self, offset, whence=0):
        if whence == 0:
            self._offset = offset
        elif whence == 1:
            self._offset += offset
        elif whence == 2:
            self._offset = self.size() + offset


def open(url):
    return _HttpRangeFileObject(url)
