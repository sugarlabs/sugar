# Copyright (C) 2006, Red Hat, Inc.
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

import random

import hippo
import gobject

from sugar.graphics.spreadbox import SpreadBox
from sugar.graphics import units
from view.home.MyIcon import MyIcon
from view.home.FriendView import FriendView

class FriendsBox(SpreadBox):
    __gtype_name__ = 'SugarFriendsBox'
    def __init__(self, shell, menu_shell):
        SpreadBox.__init__(self, background_color=0xe2e2e2ff)

        self._shell = shell
        self._menu_shell = menu_shell
        self._friends = {}

        self._my_icon = MyIcon(units.LARGE_ICON_SCALE)
        self.set_center_item(self._my_icon)

        friends = self._shell.get_model().get_friends()

        for friend in friends:
            self.add_friend(friend)

        friends.connect('friend-added', self._friend_added_cb)
        friends.connect('friend-removed', self._friend_removed_cb)

    def add_friend(self, buddy_info):
        icon = FriendView(self._shell, self._menu_shell, buddy_info)
        self.add_item(icon)

        self._friends[buddy_info.get_key()] = icon

    def _friend_added_cb(self, data_model, buddy_info):
        self.add_friend(buddy_info)

    def _friend_removed_cb(self, data_model, key):
        self.remove_item(self._friends[key])
        del self._friends[key]
