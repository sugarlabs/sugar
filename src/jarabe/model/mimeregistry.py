# Copyright (C) 2009 Aleksey Lim
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import re

from gi.repository import GConf


_DEFAULTS_KEY = '/desktop/sugar/journal/defaults'
_GCONF_INVALID_CHARS = re.compile('[^a-zA-Z0-9-_/.]')

_instance = None


class MimeRegistry(object):

    def __init__(self):
        # TODO move here all mime_type related code from jarabe modules
        self._gconf = GConf.Client.get_default()

    def get_default_activity(self, mime_type):
        return self._gconf.get_string(_key_name(mime_type))

    def set_default_activity(self, mime_type, bundle_id):
        self._gconf.set_string(_key_name(mime_type), bundle_id)


def get_registry():
    global _instance
    if _instance is None:
        _instance = MimeRegistry()
    return _instance


def _key_name(mime_type):
    mime_type = _GCONF_INVALID_CHARS.sub('_', mime_type)
    return '%s/%s' % (_DEFAULTS_KEY, mime_type)
