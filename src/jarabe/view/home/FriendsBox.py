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

import gobject
import gtk
import hippo

from sugar import profile
from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon, Icon
from sugar.graphics.palette import Palette

from jarabe.model import shellmodel
from jarabe.view.home.FriendView import FriendView
from jarabe.view.home.spreadlayout import SpreadLayout

class FriendsBox(hippo.Canvas):
    __gtype_name__ = 'SugarFriendsBox'
    def __init__(self):
        gobject.GObject.__init__(self)

        self._box = hippo.CanvasBox()
        self._box.props.background_color = style.COLOR_WHITE.get_int()
        self.set_root(self._box)

        self._friends = {}

        self._layout = SpreadLayout()
        self._box.set_layout(self._layout)

        self._owner_icon = CanvasIcon(icon_name='computer-xo', cache=True,
                                      xo_color=profile.get_color())
        self._owner_icon.props.size = style.LARGE_ICON_SIZE
        palette_icon = Icon(icon_name='computer-xo',
                            xo_color=profile.get_color())
        palette_icon.props.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
        palette = Palette(None, primary_text=profile.get_nick_name(),
                          icon=palette_icon)
        self._owner_icon.set_palette(palette)
        self._layout.add(self._owner_icon)

        friends = shellmodel.get_instance().get_friends()

        for friend in friends:
            self.add_friend(friend)

        friends.connect('friend-added', self._friend_added_cb)
        friends.connect('friend-removed', self._friend_removed_cb)

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

