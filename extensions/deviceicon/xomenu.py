# Copyright (C) 2008 Ryan Kabir
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
import gconf

import gtk

from sugar.graphics.menuitem import MenuItem
from sugar.graphics.tray import TrayIcon
from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.controlpanel.gui import ControlPanel
from jarabe.model.session import get_session_manager

_ICON_NAME = 'computer-xo'


class SystemView(TrayIcon):

    FRAME_POSITION_RELATIVE = 800

    def __init__(self):
        client = gconf.client_get_default()        
        color = XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=color)

    def create_palette(self):
        palette = SystemPalette(_('System functions') )
        palette.props.invoker = FrameWidgetInvoker(self)
        palette.set_group_id('frame')
        return palette

class SystemPalette(Palette):
    def __init__(self, primary_text):
        Palette.__init__(self, label=primary_text)

        item = MenuItem(_('Settings'), 'preferences-system')
        item.connect('activate', self.__controlpanel_activate_cb)
        self.menu.append(item)
        item.show()

        item = MenuItem(_('Restart'), 'system-restart')
        item.connect('activate', self.__reboot_activate_cb)
        self.menu.append(item)
        item.show()

        item = MenuItem(_('Shutdown'), 'system-shutdown')
        item.connect('activate', self.__shutdown_activate_cb)
        self.menu.append(item)
        item.show()

    def __reboot_activate_cb(self, menu_item):
        session_manager = get_session_manager()
        session_manager.reboot()

    def __shutdown_activate_cb(self, menu_item):
        session_manager = get_session_manager()
        session_manager.shutdown()
        
    def __controlpanel_activate_cb(self, menu_item):
        panel = ControlPanel()
        panel.set_transient_for(self.get_toplevel())
        panel.show()


def setup(tray):
    tray.add_device(SystemView())
