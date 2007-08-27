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

import hippo
import logging

from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor
from sugar.graphics.iconbutton import IconButton
from sugar.graphics import style
from sugar import profile
from sugar import activity

from frameinvoker import FrameCanvasInvoker

class ActivityButton(IconButton):
    def __init__(self, activity_info):
        IconButton.__init__(self, icon_name=activity_info.icon,
                            stroke_color=style.COLOR_WHITE,
                            fill_color=style.COLOR_TRANSPARENT)

        palette = Palette(activity_info.name)
        palette.props.invoker = FrameCanvasInvoker(self)
        palette.set_group_id('frame')
        self.set_palette(palette)

        self._activity_info = activity_info

    def get_bundle_id(self):
        return self._activity_info.service_name

class InviteButton(IconButton):
    def __init__(self, activity_model, invite):
        IconButton.__init__(self, icon_name=activity_model.get_color())

        self.props.xo_color = activity_model.get_color()
        self._invite = invite

    def get_activity_id(self):
        return self._invite.get_activity_id()

    def get_bundle_id(self):
        return self._invite.get_bundle_id()

    def get_invite(self):
        return self._invite

class ActivitiesBox(hippo.CanvasBox):
    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell
        self._shell_model = self._shell.get_model() 
        self._invite_to_item = {}
        self._invites = self._shell_model.get_invites()

        registry = activity.get_registry()
        registry.get_activities_async(reply_handler=self._get_activities_cb)

        registry.connect('activity-added', self._activity_added_cb)

        for invite in self._invites:
            self.add_invite(invite)
        self._invites.connect('invite-added', self._invite_added_cb)
        self._invites.connect('invite-removed', self._invite_removed_cb)

    def _get_activities_cb(self, activity_list):
        for activity_info in activity_list:
            if activity_info.show_launcher:
                self.add_activity(activity_info)

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

    def _activity_added_cb(self, activity_registry, activity_info):
        self.add_activity(activity_info)

    def add_activity(self, activity_info):
        item = ActivityButton(activity_info)
        item.connect('activated', self._activity_clicked_cb)
        self.append(item, 0)

    def add_invite(self, invite):
        mesh = self._shell_model.get_mesh()
        activity_model = mesh.get_activity(invite.get_activity_id())
        if activity:
            item = InviteButton(activity_model, invite)
            item.connect('activated', self._invite_clicked_cb)
            self.append(item, 0)

            self._invite_to_item[invite] = item

    def remove_invite(self, invite):
        self.remove(self._invite_to_item[invite])
        del self._invite_to_item[invite]
