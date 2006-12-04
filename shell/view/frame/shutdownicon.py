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

import dbus

from sugar.graphics.menuicon import MenuIcon
from sugar.graphics.menu import Menu
from sugar.graphics import style

class ShutdownIcon(MenuIcon):
    ACTION_SHUTDOWN = 2

    def __init__(self, menu_shell):
        MenuIcon.__init__(self, menu_shell, icon_name='stock-close')
        style.apply_stylesheet(self, 'menu.ActionIcon')

    def create_menu(self):
        menu = Menu()
        menu.add_item('Shut Down', ShutdownIcon.ACTION_SHUTDOWN)
        menu.connect('action', self._action_cb)
        return menu

    def _action_cb(self, menu, action):
        self.popdown()

        if action == ShutdownIcon.ACTION_SHUTDOWN:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.Hal',
                                   '/org/freedesktop/Hal/devices/computer')
            mgr = dbus.Interface(proxy, 'org.freedesktop.Hal.Device.SystemPowerManagement')
            mgr.Shutdown()
