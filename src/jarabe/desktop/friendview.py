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

from sugar.graphics.icon import CanvasIcon
from sugar.graphics import style
from sugar.presence import presenceservice
from sugar import activity

from jarabe.view.BuddyIcon import BuddyIcon

class FriendView(hippo.CanvasBox):
    def __init__(self, buddy, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        self._pservice = presenceservice.get_instance()

        self._buddy = buddy
        self._buddy_icon = BuddyIcon(buddy)
        self._buddy_icon.props.size = style.LARGE_ICON_SIZE
        self.append(self._buddy_icon)

        self._activity_icon = CanvasIcon(size=style.LARGE_ICON_SIZE)
        self._activity_icon_visible = False

        if self._buddy.is_present():
            self._buddy_appeared_cb(buddy)

        self._buddy.connect('current-activity-changed',
                            self._buddy_activity_changed_cb)
        self._buddy.connect('appeared', self._buddy_appeared_cb)
        self._buddy.connect('disappeared', self._buddy_disappeared_cb)
        self._buddy.connect('color-changed', self._buddy_color_changed_cb)

    def _get_new_icon_name(self, ps_activity):
        registry = activity.get_registry()
        activity_info = registry.get_activity(ps_activity.props.type)
        if activity_info:
            return activity_info.icon
        return None

    def _remove_activity_icon(self):
        if self._activity_icon_visible:
            self.remove(self._activity_icon)
            self._activity_icon_visible = False

    def _buddy_activity_changed_cb(self, buddy, ps_activity=None):
        if not ps_activity:
            self._remove_activity_icon()
            return

        # FIXME: use some sort of "unknown activity" icon rather
        # than hiding the icon?
        name = self._get_new_icon_name(ps_activity)
        if name:
            self._activity_icon.props.file_name = name
            self._activity_icon.props.xo_color = buddy.get_color()
            if not self._activity_icon_visible:
                self.append(self._activity_icon, hippo.PACK_EXPAND)
                self._activity_icon_visible = True
        else:
            self._remove_activity_icon()

    def _buddy_appeared_cb(self, buddy):
        home_activity = self._buddy.get_current_activity()
        self._buddy_activity_changed_cb(buddy, home_activity)

    def _buddy_disappeared_cb(self, buddy):
        self._buddy_activity_changed_cb(buddy, None)

    def _buddy_color_changed_cb(self, buddy, color):
        # TODO: shouldn't this change self._buddy_icon instead?
        self._activity_icon.props.xo_color = buddy.get_color()
