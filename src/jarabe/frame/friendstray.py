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

from sugar3.graphics.tray import VTray, TrayIcon

from jarabe.view.buddymenu import BuddyMenu
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import shell
from jarabe.model.buddy import get_owner_instance
from jarabe.model import neighborhood


class FriendIcon(TrayIcon):

    def __init__(self, buddy):
        TrayIcon.__init__(self, icon_name='computer-xo',
                          xo_color=buddy.get_color())

        self._buddy = buddy
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.cache_palette = False
        self.palette_invoker.props.toggle_palette = True

    def create_palette(self):
        palette = BuddyMenu(self._buddy)
        palette.props.icon_visible = False
        palette.set_group_id('frame')
        return palette


class FriendsTray(VTray):

    def __init__(self):
        VTray.__init__(self)

        self._shared_activity = None
        self._buddies = {}

        shell.get_model().connect('active-activity-changed',
                                  self.__active_activity_changed_cb)

        neighborhood.get_model().connect('activity-added',
                                         self.__neighborhood_activity_added_cb)

    def add_buddy(self, buddy):
        if buddy.props.key in self._buddies:
            return

        icon = FriendIcon(buddy)
        self.add_item(icon)
        icon.show()

        self._buddies[buddy.props.key] = icon

    def remove_buddy(self, buddy):
        if buddy.props.key not in self._buddies:
            return

        self.remove_item(self._buddies[buddy.props.key])
        del self._buddies[buddy.props.key]

    def clear(self):
        for item in self.get_children():
            self.remove_item(item)
            item.destroy()
        self._buddies = {}

    def __neighborhood_activity_added_cb(self, neighborhood_model,
                                         shared_activity):
        logging.debug('FriendsTray.__neighborhood_activity_added_cb')
        active_activity = shell.get_model().get_active_activity()
        if active_activity.get_activity_id() != shared_activity.activity_id:
            return

        self.clear()

        # always display ourselves
        self.add_buddy(get_owner_instance())

        self._set_current_activity(shared_activity.activity_id)

    def __active_activity_changed_cb(self, home_model, home_activity):
        logging.debug('FriendsTray.__active_activity_changed_cb')
        self.clear()

        # always display ourselves
        self.add_buddy(get_owner_instance())

        if home_activity is None:
            return

        activity_id = home_activity.get_activity_id()
        if activity_id is None:
            return

        self._set_current_activity(activity_id)

    def _set_current_activity(self, activity_id):
        logging.debug('FriendsTray._set_current_activity')
        neighborhood_model = neighborhood.get_model()
        self._shared_activity = neighborhood_model.get_activity(activity_id)
        if self._shared_activity is None:
            return

        for buddy in self._shared_activity.get_buddies():
            self.add_buddy(buddy)

        self._shared_activity.connect('buddy-added', self.__buddy_added_cb)
        self._shared_activity.connect('buddy-removed', self.__buddy_removed_cb)

    def __buddy_added_cb(self, activity, buddy):
        logging.debug('FriendsTray.__buddy_added_cb')
        self.add_buddy(buddy)

    def __buddy_removed_cb(self, activity, buddy):
        logging.debug('FriendsTray.__buddy_removed_cb')
        self.remove_buddy(buddy)
