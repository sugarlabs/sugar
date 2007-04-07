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
from gettext import gettext as _

import gtk
import gobject
import hippo

from sugar.graphics.menu import Menu, MenuItem
from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import units
from sugar.presence import PresenceService

class BuddyMenu(Menu):
    ACTION_MAKE_FRIEND = 0
    ACTION_INVITE = 1
    ACTION_REMOVE_FRIEND = 2

    def __init__(self, shell, buddy):
        self._buddy = buddy
        self._shell = shell

        Menu.__init__(self, buddy.get_name())
        self.props.border = 0
        self.props.padding = units.points_to_pixels(5)
        pixbuf = self._get_buddy_icon_pixbuf()
        if pixbuf:
            icon_item = hippo.CanvasImage()
            scaled_pixbuf = pixbuf.scale_simple(units.grid_to_pixels(1),
                                                units.grid_to_pixels(1),
                                                gtk.gdk.INTERP_BILINEAR)
            del pixbuf
            self.add_separator()
            self.append(icon_item)
            # FIXME: have to set the image _after_ adding the HippoCanvasImage
            # to it's parent item, because that sets the HippoCanvasImage's context,
            # which resets the object's 'image' property.  Grr.
            #_sugar.hippo_canvas_image_set_image_from_gdk_pixbuf(icon_item, scaled_pixbuf)

        self._buddy.connect('icon-changed', self.__buddy_icon_changed_cb)

        owner = shell.get_model().get_owner()
        if buddy.get_name() != owner.get_name():
            self._add_items()

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

    def _add_items(self):
        shell_model = self._shell.get_model()
        pservice = PresenceService.get_instance()

        friends = shell_model.get_friends()
        if friends.has_buddy(self._buddy):
            self.add_item(MenuItem(BuddyMenu.ACTION_REMOVE_FRIEND,
                                   _('Remove friend'),
                                   'theme:stock-remove'))
        else:
            self.add_item(MenuItem(BuddyMenu.ACTION_MAKE_FRIEND,
                                   _('Make friend'),
                                   'theme:stock-add'))

        activity = shell_model.get_home().get_current_activity()
        if activity != None:
            activity_ps = pservice.get_activity(activity.get_id())

            # FIXME check that the buddy is not in the activity already

            self.add_item(MenuItem(BuddyMenu.ACTION_INVITE,
                                   _('Invite'),
                                   'theme:stock-invite'))

    def __buddy_icon_changed_cb(self, buddy):
        pass
