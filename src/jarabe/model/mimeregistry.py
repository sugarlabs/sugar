# Copyright (C) 2009 Aleksey Lim
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

from gi.repository import GLib
from gi.repository import Gio

_JOURNAL_DIR = 'org.sugarlabs.journal'
_REGISTRY_KEY = 'mime-registry'

_instance = None


class MimeRegistry(object):

    def __init__(self):
        # TODO move here all mime_type related code from jarabe modules
        self._settings = Gio.Settings(_JOURNAL_DIR)

    def get_default_activity(self, mime_type):
        dictionary = self._settings.get_value(_REGISTRY_KEY).unpack()
        return dictionary.get(mime_type)

    def set_default_activity(self, mime_type, bundle_id):
        dictionary = self._settings.get_value(_REGISTRY_KEY).unpack()
        dictionary[mime_type] = bundle_id

        variant = GLib.Variant('a{ss}', dictionary)
        self._settings.set_value(_REGISTRY_KEY, variant)


def get_registry():
    global _instance
    if _instance is None:
        _instance = MimeRegistry()
    return _instance
