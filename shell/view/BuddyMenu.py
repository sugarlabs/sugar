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

import gtk
import gobject
import hippo

from sugar.graphics.menu import Menu
from sugar.graphics.canvasicon import CanvasIcon
from sugar.presence import PresenceService

_ICON_SIZE = 75

class BuddyMenu(Menu):
    ACTION_MAKE_FRIEND = 0
    ACTION_INVITE = 1
    ACTION_REMOVE_FRIEND = 2

    def __init__(self, shell, buddy):
        self._buddy = buddy
        self._shell = shell

        icon_item = None
        pixbuf = self._get_buddy_icon_pixbuf()
        if pixbuf:
            scaled_pixbuf = pixbuf.scale_simple(_ICON_SIZE, _ICON_SIZE,
                                                gtk.gdk.INTERP_BILINEAR)
            del pixbuf
            icon_item = hippo.CanvasImage(pixbuf=scaled_pixbuf)

        Menu.__init__(self, buddy.get_name(), icon_item)

        self._buddy.connect('icon-changed', self.__buddy_icon_changed_cb)

        owner = shell.get_model().get_owner()
        if buddy.get_name() != owner.get_name():
            self._add_actions()

    def _get_buddy_icon_pixbuf(self):
        buddy_object = self._buddy.get_buddy()
        if not buddy_object:
            return None

        pixbuf = None
        icon_data = buddy_object.get_icon()
        icon_data_string = ""
        for item in icon_data:
            if item < 0:
                item = item + 128
            icon_data_string += chr(item)
        pbl = gtk.gdk.PixbufLoader()
        pbl.write(icon_data_string)
        try:
            pbl.close()
            pixbuf = pbl.get_pixbuf()
        except gobject.GError:
            pass
        del pbl
        return pixbuf

    def _add_actions(self):
        shell_model = self._shell.get_model()
        pservice = PresenceService.get_instance()

        friends = shell_model.get_friends()
        if friends.has_buddy(self._buddy):
            icon = CanvasIcon(icon_name='stock-remove')
            self.add_action(icon, BuddyMenu.ACTION_REMOVE_FRIEND) 
        else:
            icon = CanvasIcon(icon_name='stock-add')
            self.add_action(icon, BuddyMenu.ACTION_MAKE_FRIEND)

        activity_id = shell_model.get_current_activity()
        if activity_id != None:
            activity_ps = pservice.get_activity(activity_id)

            # FIXME check that the buddy is not in the activity already

            icon = CanvasIcon(icon_name='stock-invite')
            self.add_action(icon, BuddyMenu.ACTION_INVITE)

    def __buddy_icon_changed_cb(self, buddy):
        pass

