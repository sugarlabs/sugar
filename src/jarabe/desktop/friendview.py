# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon

from jarabe.view.buddyicon import BuddyIcon
from jarabe.model import bundleregistry


class FriendView(Gtk.VBox):

    def __init__(self, buddy, **kwargs):
        Gtk.VBox.__init__(self)

        # round icon sizes to an even number so that it can be accurately
        # centered in a larger bounding box also of even dimensions
        size = style.LARGE_ICON_SIZE & ~1

        self._buddy = buddy
        self._buddy_icon = BuddyIcon(buddy)
        self._buddy_icon.props.pixel_size = size
        self.add(self._buddy_icon)
        self._buddy_icon.show()

        self._activity_icon = CanvasIcon(pixel_size=size)
        self._update_activity()

        self._buddy.connect('notify::current-activity',
                            self.__buddy_notify_current_activity_cb)
        self._buddy.connect('notify::present', self.__buddy_notify_present_cb)
        self._buddy.connect('notify::color', self.__buddy_notify_color_cb)

    def _get_new_icon_name(self, ps_activity):
        registry = bundleregistry.get_registry()
        activity_info = registry.get_bundle(ps_activity.props.type)
        if activity_info:
            return activity_info.get_icon()
        return None

    def _remove_activity_icon(self):
        if self._activity_icon.get_visible():
            self._activity_icon.hide()
            self.remove(self._activity_icon)

    def __buddy_notify_current_activity_cb(self, buddy, pspec):
        self._update_activity()

    def _update_activity(self):
        if not self._buddy.props.present or \
           not self._buddy.props.current_activity:
            self._remove_activity_icon()
            return

        # FIXME: use some sort of "unknown activity" icon rather
        # than hiding the icon?
        name = self._get_new_icon_name(self._buddy.current_activity)
        if name:
            self._activity_icon.props.file_name = name
            self._activity_icon.props.xo_color = self._buddy.props.color
            if not self._activity_icon.get_visible():
                self.add(self._activity_icon)
                self._activity_icon.show()
        else:
            self._remove_activity_icon()

    def __buddy_notify_present_cb(self, buddy, pspec):
        self._update_activity()

    def __buddy_notify_color_cb(self, buddy, pspec):
        # TODO: shouldn't this change self._buddy_icon instead?
        self._activity_icon.props.xo_color = buddy.props.color
