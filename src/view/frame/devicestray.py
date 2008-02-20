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

import logging
from gettext import gettext as _

import gtk

from sugar.graphics.tray import HTray
from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem

from view.frame.frameinvoker import FrameWidgetInvoker
from view.devices import deviceview

class DevicesTray(HTray):
    def __init__(self, shell):
        HTray.__init__(self)
        self._device_icons = {}

        devices_model = shell.get_model().get_devices()

        for device in devices_model:
            self._add_device(device)

        devices_model.connect('device-appeared',
                              self.__device_appeared_cb)
        devices_model.connect('device-disappeared',
                              self.__device_disappeared_cb)

    def _add_device(self, device):
        view = deviceview.create(device)
        self.pack_end(view, expand=False, fill=False, padding=0)
        view.show()
        self._device_icons[device.get_id()] = view

    def _remove_device(self, device):
        self.remove_item(self._device_icons[device.get_id()])
        del self._device_icons[device.get_id()]

    def __device_appeared_cb(self, model, device):
        self._add_device(device)

    def __device_disappeared_cb(self, model, device):
        self._remove_device(device)

