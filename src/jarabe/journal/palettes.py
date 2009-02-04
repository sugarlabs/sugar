# Copyright (C) 2008 One Laptop Per Child
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

import gobject
import gtk
import gconf

from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor
from sugar import mime

from jarabe.model import bundleregistry
from jarabe.model import friends
from jarabe.model import filetransfer
from jarabe.journal import misc
from jarabe.journal import model

class ObjectPalette(Palette):

    __gtype_name__ = 'ObjectPalette'

    __gsignals__ = {
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([]))
    }

    def __init__(self, metadata, detail=False):

        self._metadata = metadata
        self._temp_file_path = None

        activity_icon = Icon(icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
        activity_icon.props.file = misc.get_icon_name(metadata)
        if metadata.has_key('icon-color') and \
                metadata['icon-color']:
            activity_icon.props.xo_color = \
                XoColor(metadata['icon-color'])
        else:
            activity_icon.props.xo_color = \
                XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                   style.COLOR_TRANSPARENT.get_svg()))
        
        if metadata.has_key('title'):
            title = metadata['title']
        else:
            title = _('Untitled')

        Palette.__init__(self, primary_text=title,
                         icon=activity_icon)

        if metadata.get('activity_id', ''):
            resume_label = _('Resume')
            resume_with_label = _('Resume with')
        else:
            resume_label = _('Start')
            resume_with_label = _('Start with')
        menu_item = MenuItem(resume_label, 'activity-start')
        menu_item.connect('activate', self.__start_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(resume_with_label, 'activity-start')
        self.menu.append(menu_item)
        menu_item.show()
        start_with_menu = StartWithMenu(self._metadata)
        menu_item.set_submenu(start_with_menu)

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        menu_item = MenuItem(_('Copy'))
        icon = Icon(icon_name='edit-copy', xo_color=color,
                    icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        menu_item.connect('activate', self.__copy_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        menu_item = MenuItem(_('Send to'), 'document-send')
        self.menu.append(menu_item)
        menu_item.show()

        friends_menu = FriendsMenu()
        friends_menu.connect('friend-selected', self.__friend_selected_cb)
        menu_item.set_submenu(friends_menu)

        if detail == True:
            menu_item = MenuItem(_('View Details'), 'go-right')
            menu_item.connect('activate', self.__detail_activate_cb)
            self.menu.append(menu_item)
            menu_item.show()

        menu_item = MenuItem(_('Erase'), 'list-remove')
        menu_item.connect('activate', self.__erase_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __start_activate_cb(self, menu_item):
        misc.resume(self._metadata)

    def __copy_activate_cb(self, menu_item):
        clipboard = gtk.Clipboard()
        clipboard.set_with_data([('text/uri-list', 0, 0)],
                                self.__clipboard_get_func_cb,
                                self.__clipboard_clear_func_cb)

    def __clipboard_get_func_cb(self, clipboard, selection_data, info, data):
        # Get hold of a reference so the temp file doesn't get deleted
        self._temp_file_path = model.get_file(self._metadata['uid'])
        logging.debug('__clipboard_get_func_cb %r' % self._temp_file_path)
        selection_data.set_uris(['file://' + self._temp_file_path])

    def __clipboard_clear_func_cb(self, clipboard, data):
        # Release and delete the temp file
        self._temp_file_path = None

    def __erase_activate_cb(self, menu_item):
        registry = bundleregistry.get_registry()

        bundle = misc.get_bundle(self._metadata)
        if bundle is not None and registry.is_installed(bundle):
            registry.uninstall(bundle)
        model.delete(self._metadata['uid'])

    def __detail_activate_cb(self, menu_item):
        self.emit('detail-clicked')

    def __friend_selected_cb(self, menu_item, buddy):
        logging.debug('__friend_selected_cb')
        file_name = model.get_file(self._metadata['uid'])

        title = str(self._metadata['title'])
        description = str(self._metadata.get('description', ''))
        mime_type = str(self._metadata['mime_type'])

        if not mime_type:
            mime_type = mime.get_for_file(file_name)

        filetransfer.start_transfer(buddy, file_name, title, description,
                                    mime_type)

class FriendsMenu(gtk.Menu):
    __gtype_name__ = 'JournalFriendsMenu'

    __gsignals__ = {
        'friend-selected'  : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                              ([object])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        if filetransfer.file_transfer_available():
            friends_model = friends.get_model()
            for friend in friends_model:
                if friend.is_present():
                    menu_item = MenuItem(text_label=friend.get_nick(), 
                                         icon_name='computer-xo',
                                         xo_color=friend.get_color())
                    menu_item.connect('activate', self.__item_activate_cb,
                                      friend)
                    self.append(menu_item)
                    menu_item.show()

            if not self.get_children():
                menu_item = MenuItem(_('No friends present'))
                menu_item.set_sensitive(False)
                self.append(menu_item)
                menu_item.show()            
        else:
            menu_item = MenuItem(_('No valid connection found'))
            menu_item.set_sensitive(False)
            self.append(menu_item)
            menu_item.show()            

    def __item_activate_cb(self, menu_item, friend):
        self.emit('friend-selected', friend)


class StartWithMenu(gtk.Menu):
    __gtype_name__ = 'JournalStartWithMenu'

    def __init__(self, metadata):
        gobject.GObject.__init__(self)

        self._metadata = metadata

        for activity_info in misc.get_activities(metadata):
            menu_item = MenuItem(activity_info.get_name())
            menu_item.set_image(Icon(file=activity_info.get_icon(),
                                     icon_size=gtk.ICON_SIZE_MENU))
            menu_item.connect('activate', self.__item_activate_cb,
                              activity_info.get_bundle_id())
            self.append(menu_item)
            menu_item.show()

        if not self.get_children():
            if metadata.get('activity_id', ''):
                resume_label = _('No activity to resume entry')
            else:
                resume_label = _('No activity to start entry')
            menu_item = MenuItem(resume_label)
            menu_item.set_sensitive(False)
            self.append(menu_item)
            menu_item.show()            

    def __item_activate_cb(self, menu_item, service_name):
        misc.resume(self._metadata, service_name)


class BuddyPalette(Palette):
    def __init__(self, buddy):
        self._buddy = buddy

        nick, colors = buddy
        buddy_icon = Icon(icon_name='computer-xo',
                          icon_size=style.STANDARD_ICON_SIZE,
                          xo_color=XoColor(colors))

        Palette.__init__(self, primary_text=nick,
                         icon=buddy_icon)

        # TODO: Support actions on buddies, like make friend, invite, etc.
