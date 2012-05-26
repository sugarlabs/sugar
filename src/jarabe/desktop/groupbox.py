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

import gobject
import hippo
import gconf

from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon
from sugar.graphics.xocolor import XoColor

from jarabe.view.buddymenu import BuddyMenu
from jarabe.model.buddy import get_owner_instance
from jarabe.model import friends
from jarabe.desktop.friendview import FriendView
from jarabe.desktop.spreadlayout import SpreadLayout


class GroupBox(hippo.Canvas):
    __gtype_name__ = 'SugarGroupBox'

    def __init__(self):
        logging.debug('STARTUP: Loading the group view')

        gobject.GObject.__init__(self)

        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_WHITE.get_int()
        self.set_root(self._box)

        self._friends = {}

        self._layout = SpreadLayout()
        self._box.set_layout(self._layout)

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))

        self._owner_icon = CanvasIcon(icon_name='computer-xo', cache=True,
                                      xo_color=color)
        self._owner_icon.props.size = style.LARGE_ICON_SIZE

        self._owner_icon.set_palette(BuddyMenu(get_owner_instance()))
        self._layout.add(self._owner_icon)

        friends_model = friends.get_model()

        for friend in friends_model:
            self.add_friend(friend)

        friends_model.connect('friend-added', self._friend_added_cb)
        friends_model.connect('friend-removed', self._friend_removed_cb)

    def add_friend(self, buddy_info):
        icon = FriendView(buddy_info)
        self._layout.add(icon)

        self._friends[buddy_info.get_key()] = icon

    def _friend_added_cb(self, data_model, buddy_info):
        self.add_friend(buddy_info)

    def _friend_removed_cb(self, data_model, key):
        icon = self._friends[key]
        self._layout.remove(icon)
        del self._friends[key]
        icon.destroy()

    def do_size_allocate(self, allocation):
        width = allocation.width
        height = allocation.height

        min_w_, icon_width = self._owner_icon.get_width_request()
        min_h_, icon_height = self._owner_icon.get_height_request(icon_width)
        x = (width - icon_width) / 2
        y = (height - icon_height) / 2
        self._layout.move(self._owner_icon, x, y)

        hippo.Canvas.do_size_allocate(self, allocation)
