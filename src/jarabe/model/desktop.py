# Copyright (C) 2008-2013 Sugar Labs
# Copyright (C) 2013 Walter Bender
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

from gi.repository import GObject
from gi.repository import GConf

_desktop_view_instance = None

_VIEW_ICONS = ['view-radial']
_FAVORITE_ICONS = ['emblem-favorite']

_VIEW_DIR = '/desktop/sugar/desktop'
_VIEW_ENTRY = 'view_icons'
_FAVORITE_ENTRY = 'favorite_icons'
_VIEW_KEY = '%s/%s' % (_VIEW_DIR, _VIEW_ENTRY)
_FAVORITE_KEY = '%s/%s' % (_VIEW_DIR, _FAVORITE_ENTRY)


class DesktopViewModel(GObject.GObject):
    __gtype_name__ = 'SugarDesktopViewModel'
    __gsignals__ = {
        'desktop-view-icons-changed': (GObject.SignalFlags.RUN_FIRST, None,
                                       ([]))
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._number_of_views = 1
        self._view_icons = None
        self._favorite_icons = None

        self._ensure_view_icons()

        client = GConf.Client.get_default()
        client.add_dir(_VIEW_KEY, GConf.ClientPreloadType.PRELOAD_NONE)
        self._gconf_id = client.notify_add(_VIEW_KEY, self.__gconf_changed_cb,
                                           None)

    def get_view_icons(self):
        return self._view_icons

    view_icons = GObject.property(type=object, getter=get_view_icons)

    def get_number_of_views(self):
        return self._number_of_views

    number_of_views = GObject.property(type=object, getter=get_number_of_views)

    def get_favorite_icons(self):
        return self._favorite_icons

    favorite_icons = GObject.property(type=object, getter=get_favorite_icons)

    def _ensure_view_icons(self, update=False):
        if self._view_icons is not None and not update:
            return

        client = GConf.Client.get_default()

        options = client.get(_VIEW_KEY)
        self._view_icons = []
        if options is not None:
            for gval in options.get_list():
                self._view_icons.append(gval.get_string())

        if self._view_icons is None or self._view_icons == []:
            self._view_icons = _VIEW_ICONS[:]

        self._number_of_views = len(self._view_icons)

        options = client.get(_FAVORITE_KEY)
        if options is not None:
            self._favorite_icons = []
            for gval in options.get_list():
                self._favorite_icons.append(gval.get_string())
        else:
            self._favorite_icons = _FAVORITE_ICONS[:]

        if len(self._favorite_icons) < self._number_of_views:
            for i in range(self._number_of_views - len(self._favorite_icons)):
                self._favorite_icons.append(_FAVORITE_ICONS[0])

        self.emit('desktop-view-icons-changed')

    def __del__(self):
        client = GConf.Client.get_default()
        client.notify_remove(self._gconf_id)

    def __gconf_changed_cb(self, client, timestamp, entry, *extra):
        self._ensure_view_icons(update=True)


def get_model():
    global _desktop_view_instance
    if _desktop_view_instance is None:
        _desktop_view_instance = DesktopViewModel()
    return _desktop_view_instance


def get_view_icons():
    return get_model().get_view_icons()


def get_favorite_icons():
    return get_model().get_favorite_icons()


def get_number_of_views():
    return get_model().get_number_of_views()
