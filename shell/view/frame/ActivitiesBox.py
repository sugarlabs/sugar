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
import logging

from sugar.graphics import units
from sugar.graphics.iconcolor import IconColor
from sugar.graphics.iconbutton import IconButton
from sugar.presence import PresenceService
from sugar.activity import bundleregistry
from sugar import profile

class ActivityButton(IconButton):
    def __init__(self, activity, popup_context):
        IconButton.__init__(self, icon_name=activity.get_icon(),
                                  tooltip=activity.get_name())
        self._activity = activity
        self._popup_context = popup_context

    def _mouse_motion_event_cb(self, item, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.set_property('color', self._prelight_color)
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.set_property('color', self._normal_color)

    def get_bundle_id(self):
        return self._activity.get_service_name()
    
    def get_popup_context(self):
        return self._popup_context

class InviteButton(IconButton):
    def __init__(self, activity, invite):
        IconButton.__init__(self, icon_name=activity.get_icon())

        self.props.color = activity.get_color()
        self._invite = invite

    def get_activity_id(self):
        return self._invite.get_activity_id()

    def get_bundle_id(self):
        return self._invite.get_bundle_id()

    def get_invite(self):
        return self._invite

class ActivitiesBox(hippo.CanvasBox):
    def __init__(self, shell, popup_context):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell
        self._shell_model = self._shell.get_model() 
        self._invite_to_item = {}
        self._invites = self._shell_model.get_invites()
        self._popup_context = popup_context

        bundle_registry = bundleregistry.get_registry()
        for bundle in bundle_registry:
            if bundle.get_show_launcher():
                self.add_activity(bundle)

        bundle_registry.connect('bundle-added', self._bundle_added_cb)

        for invite in self._invites:
            self.add_invite(invite)
        self._invites.connect('invite-added', self._invite_added_cb)
        self._invites.connect('invite-removed', self._invite_removed_cb)

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

    def _bundle_added_cb(self, bundle_registry, bundle):
        self.add_activity(bundle)

    def add_activity(self, activity):
        item = ActivityButton(activity, self._popup_context)
        item.connect('activated', self._activity_clicked_cb)
        self.append(item, 0)

    def add_invite(self, invite):
        mesh = self._shell_model.get_mesh()
        activity = mesh.get_activity(invite.get_activity_id())
        if activity:
            item = InviteButton(activity, invite)
            item.connect('activated', self._invite_clicked_cb)
            self.append(item, 0)

            self._invite_to_item[invite] = item

    def remove_invite(self, invite):
        self.remove(self._invite_to_item[invite])
        del self._invite_to_item[invite]
