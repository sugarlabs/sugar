# Copyright (C) 2013, Walter Bender
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

from sugar3.test import unittest

from gi.repository import Gio
from gi.repository import GLib

from jarabe.model import desktop

_DESKTOP_CONF_DIR = 'org.sugarlabs.desktop'
_HOMEVIEWS_KEY = 'homeviews'

_VIEW_ICONS = [{'layout': 'box-layout', 'view-icon': 'view-radial',
               'favorite-icon': 'emblem-locked'}]
_MOCK_LIST = [{'layout': 'box-layout', 'view-icon': 'view-radial',
               'favorite-icon': 'emblem-locked'},
              {'layout': 'ring-layout', 'view-icon': 'view-box',
               'favorite-icon': 'emblem-favorite'}]


class TestDesktopConfig(unittest.UITestCase):

    def setUp(self):
        self.target = []

        settings = Gio.Settings(_DESKTOP_CONF_DIR)
        self._save_homeviews = settings.get_value(_HOMEVIEWS_KEY)

        self.model = desktop.get_model()
        self.model.connect('desktop-view-icons-changed',
                           self.__desktop_view_icons_changed_cb)

    def __desktop_view_icons_changed_cb(self, model):
        number_of_views = desktop.get_number_of_views()
        self.assertTrue(number_of_views == len(self.target))

        view_icons = desktop.get_view_icons()
        self.assertTrue(len(view_icons) == len(self.target))

        right_view_icons = [view['view-icon'] for view in self.target]
        for i in range(len(view_icons)):
            self.assertTrue(view_icons[i] in right_view_icons)

        favorite_icons = desktop.get_favorite_icons()
        self.assertTrue(len(favorite_icons) >= len(self.target))

    def test_unset_views(self):
        self.target = _VIEW_ICONS
        with self.run_view("gtk_main"):
            settings = Gio.Settings(_DESKTOP_CONF_DIR)
            variant = GLib.Variant('aa{ss}', self.target)
            settings.set_value(_HOMEVIEWS_KEY, variant)

    def test_set_views(self):
        self.target = _MOCK_LIST
        with self.run_view("gtk_main"):
            settings = Gio.Settings(_DESKTOP_CONF_DIR)
            variant = GLib.Variant('aa{ss}', self.target)
            settings.set_value(_HOMEVIEWS_KEY, variant)

    def tearDown(self):
        self.target = self._save_homeviews.unpack()
        settings = Gio.Settings(_DESKTOP_CONF_DIR)
        settings.set_value(_HOMEVIEWS_KEY, self._save_homeviews)
