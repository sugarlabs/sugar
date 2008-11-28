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
import gconf
        
import gtk

from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor

from jarabe.model import bundleregistry
from jarabe.journal import misc
from jarabe.journal import model

class ObjectPalette(Palette):
    def __init__(self, metadata):

        self._metadata = metadata

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
        else:
            resume_label = _('Start')
        menu_item = MenuItem(resume_label, 'activity-start')
        menu_item.connect('activate', self.__start_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

        # TODO: Add "Start with" menu item

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        menu_item = MenuItem(_('Copy'))
        icon = Icon(icon_name='edit-copy', xo_color=color,
                    icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        menu_item.connect('activate', self.__copy_activate_cb)
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
        file_path = model.get_file(self._metadata['uid'])
        logging.debug('__clipboard_get_func_cb %r' % file_path)
        selection_data.set_uris(['file://' + file_path])

    def __clipboard_clear_func_cb(self, clipboard, data):
        #TODO: should we remove here the temp file created before?
        pass

    def __erase_activate_cb(self, menu_item):
        registry = bundleregistry.get_registry()

        bundle = misc.get_bundle(self._metadata)
        if bundle is not None and registry.is_installed(bundle):
            registry.uninstall(bundle)
        model.delete(self._metadata['uid'])

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
