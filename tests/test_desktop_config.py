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

from gi.repository import GConf
from gi.repository import SugarExt

from jarabe.model import desktop

_VIEW_DIR = '/desktop/sugar/desktop'
_VIEW_ENTRY = 'view_icons'
_FAVORITE_ENTRY = 'favorite_icons'
_VIEW_KEY = '%s/%s' % (_VIEW_DIR, _VIEW_ENTRY)
_FAVORITE_KEY = '%s/%s' % (_VIEW_DIR, _FAVORITE_ENTRY)

_VIEW_ICONS = ['view-radial']
_MOCK_LIST = ['view-radial', 'view-random']


class TestDesktopConfig(unittest.UITestCase):

    def setUp(self):
        self.target = []

        client = GConf.Client.get_default()

        options = client.get(_VIEW_KEY)
        if options is not None:
            self._save_view_icons = []
            for gval in options.get_list():
                self._save_view_icons.append(gval.get_string())
        else:
            self._save_view_icons = None

        options = client.get(_FAVORITE_KEY)
        if options is not None:
            self._save_favorite_icons = []
            for gval in options.get_list():
                self._save_favorite_icons.append(gval.get_string())
        else:
            self._save_favorite_icons = None

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

    def test_unset_views(self):
        self.target = _VIEW_ICONS
        with self.run_view("gtk_main"):
            client = GConf.Client.get_default()
            client.unset(_VIEW_KEY)

    def test_set_views(self):
        self.target = _MOCK_LIST
        with self.run_view("gtk_main"):
            client = GConf.Client.get_default()
            SugarExt.gconf_client_set_string_list(client, _VIEW_KEY,
                                                  _MOCK_LIST)

    def tearDown(self):
        client = GConf.Client.get_default()
        if self._save_view_icons is None:
            client.unset(_VIEW_KEY)
        else:
            SugarExt.gconf_client_set_string_list(client,
                                                  _VIEW_KEY,
                                                  self._save_view_icons)
        if self._save_favorite_icons is None:
            client.unset(_FAVORITE_KEY)
        else:
            SugarExt.gconf_client_set_string_list(client,
                                                  _FAVORITE_KEY,
                                                  self._save_favorite_icons)
