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
from gettext import gettext as _
import logging

#import gtk
import gobject
import hippo

from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.presence import presenceservice

class BuddyMenu(Palette):
    def __init__(self, shell, buddy):
        self._buddy = buddy
        self._shell = shell

        Palette.__init__(self, buddy.get_nick())

# FIXME: re-enable when buddy avatars are re-enabled
#        pixbuf = None
#        try:
#            pixbuf = self._get_buddy_icon_pixbuf()
#        except gobject.GError, e:
#            pass
#        if pixbuf:
#            scaled_pixbuf = pixbuf.scale_simple(units.grid_to_pixels(1),
#                                                units.grid_to_pixels(1),
#                                                gtk.gdk.INTERP_BILINEAR)
#            del pixbuf
#            image = gtk.Image()
#            image.set_from_pixbuf(scaled_pixbuf)
#            self.set_content(image)
#            image.show()

        self._buddy.connect('icon-changed', self._buddy_icon_changed_cb)
        self._buddy.connect('nick-changed', self._buddy_nick_changed_cb)

        owner = shell.get_model().get_owner()
        if buddy.get_nick() != owner.get_nick():
            self._add_items()

# FIXME: re-enable when buddy avatars are re-enabled
#    def _get_buddy_icon_pixbuf(self):
#        buddy_object = self._buddy.get_buddy()
#        if not buddy_object:
#            return None
#
#        icon_data = buddy_object.props.icon
#        if not icon_data:
#            return None
#        pbl = gtk.gdk.PixbufLoader()
#        pbl.write(icon_data)
#        pixbuf = None
#        try:
#            pbl.close()
#            pixbuf = pbl.get_pixbuf()
#        except gobject.GError:
#            pass
#        del pbl
#        return pixbuf

    def _add_items(self):
        shell_model = self._shell.get_model()
        pservice = presenceservice.get_instance()

        friends = shell_model.get_friends()
        if friends.has_buddy(self._buddy):
            menu_item = MenuItem(_('Remove friend'), 'list-remove')
            menu_item.connect('activate', self._remove_friend_cb)
        else:
            menu_item = MenuItem(_('Make friend'), 'list-add')
            menu_item.connect('activate', self._make_friend_cb)

        self.menu.append(menu_item)
        menu_item.show()

        self._invite_menu = MenuItem(_('Invite'))
        self._invite_menu.connect('activate', self._invite_friend_cb)
        self.menu.append(self._invite_menu)
        self._invite_menu.show()

        home_model = shell_model.get_home()
        home_model.connect('active-activity-changed',
                           self._cur_activity_changed_cb)

    def _cur_activity_changed_cb(self, home_model, activity_model):
        if activity_model is not None:
            self._invite_menu.show()
        else:
            self._invite_menu.hide()

    def _buddy_icon_changed_cb(self, buddy):
        pass

    def _buddy_nick_changed_cb(self, buddy, nick):
        self.set_primary_text(nick)

    def _make_friend_cb(self, menuitem):
        friends = self._shell.get_model().get_friends()
        friends.make_friend(self._buddy)    

    def _remove_friend_cb(self, menuitem):
        friends = self._shell.get_model().get_friends()
        friends.remove(self._buddy)

    def _invite_friend_cb(self, menuitem):
        activity = self._shell.get_current_activity()
        activity.invite(self._buddy)

