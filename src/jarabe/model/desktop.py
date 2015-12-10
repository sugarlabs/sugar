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

from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gio

_desktop_view_instance = None

_DESKTOP_CONF_DIR = 'org.sugarlabs.desktop'
_HOMEVIEWS_KEY = 'homeviews'


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
        self._view_labels = None

        self._settings = Gio.Settings(_DESKTOP_CONF_DIR)
        self._ensure_view_icons()
        self._settings.connect(
            'changed::%s' % _HOMEVIEWS_KEY, self.__conf_changed_cb)

    def get_view_icons(self):
        return self._view_icons

    view_icons = GObject.property(type=object, getter=get_view_icons)

    def get_number_of_views(self):
        return self._number_of_views

    number_of_views = GObject.property(type=object, getter=get_number_of_views)

    def get_favorite_icons(self):
        return self._favorite_icons

    favorite_icons = GObject.property(type=object, getter=get_favorite_icons)

    def get_view_labels(self):
        return self._view_labels

    favorite_icons = GObject.property(type=object, getter=get_view_labels)

    def _ensure_view_icons(self, update=False):
        if self._view_icons and not update:
            return

        homeviews = self._settings.get_value(_HOMEVIEWS_KEY).unpack()
        if not homeviews:
            # there should always be atleast one homeview
            self._settings.reset(_HOMEVIEWS_KEY)
            homeviews = self._settings.get_value(_HOMEVIEWS_KEY).unpack()

        self._number_of_views = len(homeviews)
        self._view_icons = [view['view-icon'] for view in homeviews]
        self._favorite_icons = [view['favorite-icon'] for view in homeviews]
        self._view_labels = []
        for view in homeviews:
            if not 'view-label' in view:
                view['view-label'] = _('Favorites view %d' % (
                    len(self._view_labels) + 1))
            self._view_labels.append(view['view-label'])

        self.emit('desktop-view-icons-changed')

    def __conf_changed_cb(self, settings, key):
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


def get_view_labels():
    return get_model().get_view_labels()


def get_number_of_views():
    return get_model().get_number_of_views()
