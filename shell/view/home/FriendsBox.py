# Copyright (C) 2006-2007 Red Hat, Inc.
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

from sugar import profile
from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon
from sugar.graphics.palette import Palette

from view.home.FriendView import FriendView
from view.home.spreadlayout import SpreadLayout

class FriendsBox(hippo.CanvasBox):
    __gtype_name__ = 'SugarFriendsBox'
    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff)

        self._shell = shell
        self._friends = {}

        self._layout = SpreadLayout()
        self.set_layout(self._layout)

        self._owner_icon = CanvasIcon(icon_name='computer-xo', cache=True,
                                      xo_color=profile.get_color())
        self._owner_icon.props.size = style.LARGE_ICON_SIZE
        palette = Palette(profile.get_nick_name())
        self._owner_icon.set_palette(palette)
        self._layout.add_center(self._owner_icon)

        friends = self._shell.get_model().get_friends()

        for friend in friends:
            self.add_friend(friend)

        friends.connect('friend-added', self._friend_added_cb)
        friends.connect('friend-removed', self._friend_removed_cb)

    def add_friend(self, buddy_info):
        icon = FriendView(self._shell, buddy_info)
        self._layout.add(icon)

        self._friends[buddy_info.get_key()] = icon

    def _friend_added_cb(self, data_model, buddy_info):
        self.add_friend(buddy_info)

    def _friend_removed_cb(self, data_model, key):
        self._layout.remove(self._friends[key])
        del self._friends[key]
