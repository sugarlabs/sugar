# Copyright (C) 2013, Walter Bender
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

from sugar3.test import unittest

from gi.repository import Gio

from jarabe.model import desktop

_DESKTOP_CONF_DIR = 'org.sugarlabs.desktop'
_VIEW_KEY = 'view-icons'
_FAVORITE_KEY = 'favorite-icons'
_FAVORITE_NAME_KEY = 'favorite-names'

_VIEW_ICONS = ['view-radial']
_MOCK_LIST = ['view-radial', 'view-random']


class TestDesktopConfig(unittest.UITestCase):

    def setUp(self):
        self.target = []

        settings = Gio.Settings(_DESKTOP_CONF_DIR)
        self._save_view_icons = settings.get_strv(_VIEW_KEY)
        self._save_favorite_icons = settings.get_strv(_FAVORITE_KEY)
        self._save_favorite_names = settings.get_strv(_FAVORITE_NAME_KEY)

        self.model = desktop.get_model()
        self.model.connect('desktop-view-icons-changed',
                           self.__desktop_view_icons_changed_cb)

    def __desktop_view_icons_changed_cb(self):
        number_of_views = desktop.get_number_of_views()
        self.assertTrue(number_of_views == len(self.target))

        view_icons = desktop.get_view_icons()
        self.assertTrue(len(view_icons) == len(self.target))

        for i in range(len(view_icons)):
            self.assertTrue(view_icons[i] in self.target)

        favorite_icons = desktop.get_favorite_icons()
        self.assertTrue(len(favorite_icons) >= len(self.target))

        favorite_names = desktop.get_favorite_names()
        self.assertTrue(len(favorite_names) == len(self.target))

    def test_unset_views(self):
        self.target = _VIEW_ICONS
        with self.run_view("gtk_main"):
            settings = Gio.Settings(_DESKTOP_CONF_DIR)
            settings.set_strv(_VIEW_KEY, [])

    def test_set_views(self):
        self.target = _MOCK_LIST
        with self.run_view("gtk_main"):
            settings = Gio.Settings(_DESKTOP_CONF_DIR)
            settings.set_strv(_VIEW_KEY, _MOCK_LIST)

    def tearDown(self):
        settings = Gio.Settings(_DESKTOP_CONF_DIR)
        if self._save_view_icons is None:
            settings.set_strv(_VIEW_KEY, [])
        else:
            settings.set_strv(_VIEW_KEY, self._save_view_icons)

        if self._save_favorite_icons is None:
            settings.set_strv(_FAVORITE_KEY, [])
        else:
            settings.set_strv(_FAVORITE_KEY, self._save_favorite_icons)

        if self._save_favorite_names is None:
            settings.set_strv(_FAVORITE_NAME_KEY, [])
        else:
            settings.set_strv(_FAVORITE_NAME_KEY, self._save_favorite_names)
