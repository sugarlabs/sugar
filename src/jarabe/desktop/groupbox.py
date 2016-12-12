# Copyright (C) 2006-2007 Red Hat, Inc.
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

import logging

from sugar3.graphics import style

from jarabe.view.buddyicon import BuddyIcon
from jarabe.model.buddy import get_owner_instance
from jarabe.model import friends
from jarabe.desktop.friendview import FriendView
from jarabe.desktop.viewcontainer import ViewContainer
from jarabe.desktop.favoriteslayout import SpreadLayout
from jarabe.util.normalize import normalize_string


class GroupBox(ViewContainer):
    __gtype_name__ = 'SugarGroupBox'

    def __init__(self, toolbar):
        logging.debug('STARTUP: Loading the group view')

        layout = SpreadLayout()

        # Round off icon size to an even number to ensure that the icon
        owner_icon = BuddyIcon(get_owner_instance(),
                               style.LARGE_ICON_SIZE & ~1)
        ViewContainer.__init__(self, layout, owner_icon)
        self.set_can_focus(False)

        self._query = ''
        toolbar.connect('query-changed', self._toolbar_query_changed_cb)
        toolbar.search_entry.connect('icon-press',
                                     self.__clear_icon_pressed_cb)
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

    def _toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query.decode('utf-8'))
        for icon in self.get_children():
            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def __clear_icon_pressed_cb(self, entry, icon_pos, event):
        self.grab_focus()
