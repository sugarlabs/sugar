# Copyright (C) 2016, Abhijit Patel
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

from gi.repository import GObject
from gi.repository import Gtk
from jarabe.model import friends


class FriendListModel(GObject.GObject):
    __gtype_name__ = 'FriendListModel'

    COLUMN_SELECT = 0
    COLUMN_XO_COLOR = 1
    COLUMN_NICK = 2
    COLUMN_FRIEND = 3

    _COLUMN_TYPES = {
        COLUMN_SELECT: bool,
        COLUMN_XO_COLOR: object,
        COLUMN_NICK: str,
        COLUMN_FRIEND: object
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.friend_list = friends.get_model()
        self._selected = []

        self._list_store = Gtk.ListStore(bool, object, str, object)

        for friend in self.friend_list:
            if friend.get_handle() is not None:
                nick = friend.get_nick()
                color = friend.get_color()
                row = (False, color, nick, friend)
                self._list_store.append(row)

    def get_selected(self):
        return self._selected

    def get_liststore(self):
        return self._list_store

    def is_selected(self, friend):
        return friend in self._selected

    def set_selected(self, friend, value):
        if value:
            self._selected.append(friend)
        else:
            self._selected.remove(friend)
