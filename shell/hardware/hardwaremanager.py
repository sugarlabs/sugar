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

import logging

import dbus

from _sugar import AudioManager

_HARDWARE_MANAGER_INTERFACE = 'org.laptop.HardwareManager'
_HARDWARE_MANAGER_SERVICE = 'org.laptop.HardwareManager'
_HARDWARE_MANAGER_OBJECT_PATH = '/org/laptop/HardwareManager'

COLOR_MODE = 0
B_AND_W_MODE = 1

class HardwareManager(object):
    def __init__(self):
        try:
            bus = dbus.SystemBus()
            proxy = bus.get_object(_HARDWARE_MANAGER_SERVICE,
                                   _HARDWARE_MANAGER_OBJECT_PATH)
            self._service = dbus.Interface(proxy, _HARDWARE_MANAGER_INTERFACE)
        except dbus.DBusException:
            self._service = None
            logging.error('Hardware manager service not found.')

    def set_display_mode(self, mode):
        if not self._service:
            logging.error('Cannot set display mode. Service not found.')

        self._service.set_mode(mode)

    def set_display_brightness(self, level):
        if not self._service:
            logging.error('Cannot set display brightness. Service not found.')

        self._service.set_display_brightness(level)

    def toggle_keyboard_brightness(self):
        if not self._service:
            logging.error('Cannot set keyboard brightness. Service not found.')

        if self._service.get_keyboard_brightness():
            self._service.set_keyboard_brightness(False)
        else:
            self._service.set_keyboard_brightness(True)            

def get_hardware_manager():
    return _hardware_manager

def get_audio_manager():
    return _audio_manager

_hardware_manager = HardwareManager()
_audio_manager = AudioManager()
