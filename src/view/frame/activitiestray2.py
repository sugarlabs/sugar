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

import os
import logging

from sugar.graphics.tray import TrayButton
from sugar.graphics.tray import HTray
from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar import profile
from sugar import activity
from sugar import env

from activitybutton import ActivityButton
import config

class InviteButton(TrayButton):
    def __init__(self, activity_model, invite):
        TrayButton.__init__(self)

        icon = Icon(file=activity_model.get_icon_name(),
                    xo_color=activity_model.get_color())
        self.set_icon_widget(icon)
        icon.show()

        self._invite = invite

    def get_activity_id(self):
        return self._invite.get_activity_id()

    def get_bundle_id(self):
        return self._invite.get_bundle_id()

    def get_invite(self):
        return self._invite

class ActivitiesTray(HTray):
    def __init__(self, shell):
        HTray.__init__(self)

        self._shell = shell
        self._shell_model = self._shell.get_model() 
        self._invite_to_item = {}
        self._invites = self._shell_model.get_invites()
        self._config = self._load_config()

        registry = activity.get_registry()
        registry.get_activities_async(reply_handler=self._get_activities_cb)

        registry.connect('activity-added', self._activity_added_cb)
        registry.connect('activity-removed', self._activity_removed_cb)

        for invite in self._invites:
            self.add_invite(invite)
        self._invites.connect('invite-added', self._invite_added_cb)
        self._invites.connect('invite-removed', self._invite_removed_cb)

    def _load_config(self):
        cfg = []

        f = open(os.path.join(config.data_path, 'activities.defaults'), 'r')
        for line in f.readlines():
            line = line.strip()
            if line and not line.startswith('#'):
                cfg.append(line)
        f.close()

        return cfg

    def _get_activities_cb(self, activity_list):
        known_activities = []
        unknown_activities = []
        name_to_activity = {}

        while activity_list:
            info = activity_list.pop()
            name_to_activity[info.bundle_id] = info

            if info.bundle_id in self._config:
                known_activities.append(info)
            else:
                unknown_activities.append(info)

        sorted_activities = []
        for name in self._config:
            if name in name_to_activity:
                sorted_activities.append(name_to_activity[name])

        for info in sorted_activities + unknown_activities:
            if info.show_launcher:
                self.add_activity(info)

    def _activity_clicked_cb(self, icon):
        self._shell.start_activity(icon.get_bundle_id())

    def _invite_clicked_cb(self, icon):
        self._invites.remove_invite(icon.get_invite())
        self._shell.join_activity(icon.get_bundle_id(),
                                  icon.get_activity_id())
    
    def _invite_added_cb(self, invites, invite):
        self.add_invite(invite)

    def _invite_removed_cb(self, invites, invite):
        self.remove_invite(invite)

    def _remove_activity_cb(self, item):
        self.remove_item(item)

    def _activity_added_cb(self, activity_registry, activity_info):
        self.add_activity(activity_info)

    def _activity_removed_cb(self, activity_registry, activity_info):
        for item in self.get_children():
            if item.get_bundle_id() == activity_info.bundle_id:
                self.remove_item(item)
                return

    def add_activity(self, activity_info):
        item = ActivityButton(activity_info)
        item.connect('clicked', self._activity_clicked_cb)
        item.connect('remove_activity', self._remove_activity_cb)
        self.add_item(item, -1)
        item.show()

    def add_invite(self, invite):
        mesh = self._shell_model.get_mesh()
        activity_model = mesh.get_activity(invite.get_activity_id())
        if activity:
            item = InviteButton(activity_model, invite)
            item.connect('clicked', self._invite_clicked_cb)
            self.add_item(item, 0)
            item.show()

            self._invite_to_item[invite] = item

    def remove_invite(self, invite):
        self.remove_item(self._invite_to_item[invite])
        del self._invite_to_item[invite]
