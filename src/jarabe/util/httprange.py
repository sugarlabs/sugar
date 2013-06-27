# Copyright (C) 2008-2013 One Laptop per Child
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

"""
A simple HTTP-based file-like object that supports seek() via the HTTP
Range header. This means it doesn't have to download the whole file just
to read a small part of it. Uses urllib2 as a backend.
"""

import urllib2


class _HttpRangeFileObject(object):
    def __init__(self, url):
        self._url = url
        self._size = None
        self._offset = 0

    def tell(self):
        return self._offset

    def size(self):
        if self._size is None:
            fd = urllib2.urlopen(self._url, timeout=60)
            if not "Content-Length" in fd.headers:
                raise IOError("No content length header")
            self._size = int(fd.headers["Content-Length"])
        return self._size

    def read(self, size=-1):
        if size < 0:
            end = self.size()
        else:
            end = self._offset + size

        req = urllib2.Request(self._url)
        req.headers['Range'] = "bytes=%s-%s" % (self._offset, end - 1)
        data = urllib2.urlopen(req).read()
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
