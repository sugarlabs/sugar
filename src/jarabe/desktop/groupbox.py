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

import logging

import gconf

from sugar.graphics import style
from sugar.graphics.xocolor import XoColor

from jarabe.view.buddymenu import BuddyMenu
from jarabe.view.eventicon import EventIcon
from jarabe.model.buddy import get_owner_instance
from jarabe.model import friends
from jarabe.desktop.friendview import FriendView
from jarabe.desktop.viewcontainer import ViewContainer
from jarabe.desktop.favoriteslayout import SpreadLayout


class GroupBox(ViewContainer):
    __gtype_name__ = 'SugarGroupBox'

    def __init__(self):
        logging.debug('STARTUP: Loading the group view')

        layout = SpreadLayout()

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        owner_icon = EventIcon(icon_name='computer-xo', cache=True,
                               xo_color=color)
        # Round off icon size to an even number to ensure that the icon
        # is placed evenly in the grid
        owner_icon.props.pixel_size = style.LARGE_ICON_SIZE & ~1
        owner_icon.set_palette(BuddyMenu(get_owner_instance()))

        ViewContainer.__init__(self, layout, owner_icon)

        self._friends = {}

        friends_model = friends.get_model()

        for friend in friends_model:
            self.add_friend(friend)

        friends_model.connect('friend-added', self._friend_added_cb)
        friends_model.connect('friend-removed', self._friend_removed_cb)

    def add_friend(self, buddy_info):
        icon = FriendView(buddy_info)
        self.add(icon)
        self._friends[buddy_info.get_key()] = icon
        icon.show()

    def _friend_added_cb(self, data_model, buddy_info):
        self.add_friend(buddy_info)

    def _friend_removed_cb(self, data_model, key):
        icon = self._friends[key]
        self.remove(icon)
        del self._friends[key]
        icon.destroy()
