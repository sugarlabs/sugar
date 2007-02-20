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

import hippo

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.iconcolor import IconColor
from sugar.presence import PresenceService
from view.BuddyIcon import BuddyIcon
from model.BuddyModel import BuddyModel

class FriendsBox(hippo.CanvasBox):
    def __init__(self, shell, menu_shell):
        hippo.CanvasBox.__init__(self)
        self._shell = shell
        self._menu_shell = menu_shell
        self._activity_ps = None
        self._joined_hid = -1
        self._left_hid = -1
        self._buddies = {}

        self._pservice = PresenceService.get_instance()
        self._pservice.connect('activity-appeared',
                               self.__activity_appeared_cb)

        # Add initial activities the PS knows about
        for activity in self._pservice.get_activities():
            self.__activity_appeared_cb(self._pservice, activity)

        home_model = shell.get_model().get_home()
        home_model.connect('active-activity-changed',
                           self._active_activity_changed_cb)

    def add_buddy(self, buddy):
        if self._buddies.has_key(buddy.get_name()):
            return

        model = BuddyModel(buddy=buddy)
        icon = BuddyIcon(self._shell, self._menu_shell, model)
        self.append(icon)

        self._buddies[buddy.get_name()] = icon

    def remove_buddy(self, buddy):
        if not self._buddies.has_key(buddy.get_name()):
            return

        self.remove(self._buddies[buddy.get_name()])

    def clear(self):
        for item in self.get_children():
            self.remove(item)
        self._buddies = {}

    def __activity_appeared_cb(self, pservice, activity_ps):
        activity = self._shell.get_current_activity()
        if activity and activity_ps.get_id() == activity.get_id():
            self._set_activity_ps(activity_ps)

    def _set_activity_ps(self, activity_ps):
        if self._activity_ps == activity_ps:
            return

        if self._joined_hid > 0:
            self._activity_ps.disconnect(self._joined_hid)
            self._joined_hid = -1
        if self._left_hid > 0:
            self._activity_ps.disconnect(self._left_hid)
            self._left_hid = -1

        self._activity_ps = activity_ps

        self.clear()

        if activity_ps != None:
            for buddy in activity_ps.get_joined_buddies():
                self.add_buddy(buddy)

            self._joined_hid = activity_ps.connect(
                            'buddy-joined', self.__buddy_joined_cb)
            self._left_hid = activity_ps.connect(
                            'buddy-left', self.__buddy_left_cb)

    def _active_activity_changed_cb(self, home_model, home_activity):
        if home_activity:
            activity_id = home_activity.get_id()
            ps = self._pservice.get_activity(activity_id)
            self._set_activity_ps(ps)
        else:
            self._set_activity_ps(None)

    def __buddy_joined_cb(self, activity, buddy):
        self.add_buddy(buddy)

    def __buddy_left_cb(self, activity, buddy):
        self.remove_buddy(buddy)
