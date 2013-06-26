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

import unittest

from gi.repository import GConf
from gi.repository import SugarExt

from jarabe.desktop.config import get_view_icons, get_favorite_icons, \
    get_number_of_views, ensure_view_icons

_VIEW_KEY = '/desktop/sugar/desktop/view_icons'
_FAVORITE_KEY = '/desktop/sugar/desktop/favorite_icons'
_MOCK_LIST = ['view-radial', 'view-random']


class TestDesktopConfig(unittest.TestCase):
    def setUp(self):
        self._gconf_client = GConf.Client.get_default()

        options = self._gconf_client.get(_VIEW_KEY)
        if options is not None:
            self._save_view_icons = []
            for gval in options.get_list():
                self._save_view_icons.append(gval.get_string())
        else:
            self._save_view_icons = None

        options = self._gconf_client.get(_FAVORITE_KEY)
        if options is not None:
            self._save_favorite_icons = []
            for gval in options.get_list():
                self._save_favorite_icons.append(gval.get_string())
        else:
            self._save_favorite_icons = None

    def test_get_views(self):
        self.assertTrue(get_number_of_views() > 0)

        self._gconf_client.unset(_VIEW_KEY)
        ensure_view_icons(reload=True)
        self.assertTrue(get_number_of_views() == 1)

        SugarExt.gconf_client_set_string_list(self._gconf_client,
                                              _VIEW_KEY,
                                              _MOCK_LIST)
        ensure_view_icons(reload=True)
        self.assertTrue(get_number_of_views() == 2)

        view_icons = get_view_icons()
        self.assertTrue(len(view_icons) == len(_MOCK_LIST))

        for i in range(len(view_icons)):
            self.assertTrue(view_icons[i] == _MOCK_LIST[i])

        favorite_icons = get_favorite_icons()
        self.assertTrue(len(favorite_icons) == len(_MOCK_LIST))

        self._gconf_client.unset(_FAVORITE_KEY)
        ensure_view_icons(reload=True)
        self.assertTrue(len(get_favorite_icons()) == get_number_of_views())

    def tearDown(self):
        if self._save_view_icons is None:
            self._gconf_client.unset(_VIEW_KEY)
        else:
            SugarExt.gconf_client_set_string_list(self._gconf_client,
                                                  _VIEW_KEY,
                                                  self._save_view_icons)
        if self._save_favorite_icons is None:
            self._gconf_client.unset(_FAVORITE_KEY)
        else:
            SugarExt.gconf_client_set_string_list(self._gconf_client,
                                                  _FAVORITE_KEY,
                                                  self._save_favorite_icons)
        ensure_view_icons(reload=True)
