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

import logging

import dbus
import gobject

from jarabe.hardware.nmclient import NMClient
from sugar.profile import get_profile
from sugar import env
from sugar import _sugarext

_HARDWARE_MANAGER_INTERFACE = 'org.freedesktop.ohm.Keystore'
_HARDWARE_MANAGER_SERVICE = 'org.freedesktop.ohm'
_HARDWARE_MANAGER_OBJECT_PATH = '/org/freedesktop/ohm/Keystore'

COLOR_MODE = 0
B_AND_W_MODE = 1

VOL_CHANGE_INCREMENT_RECOMMENDATION = 10

class HardwareManager(gobject.GObject):
    __gsignals__ = {
        'muted-changed' : (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([gobject.TYPE_BOOLEAN, gobject.TYPE_BOOLEAN])),
        'volume-changed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([gobject.TYPE_INT, gobject.TYPE_INT])),
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        bus = dbus.SystemBus()
        proxy = bus.get_object(_HARDWARE_MANAGER_SERVICE,
                                _HARDWARE_MANAGER_OBJECT_PATH,
                                follow_name_owner_changes=True)
        self._service = dbus.Interface(proxy, _HARDWARE_MANAGER_INTERFACE)

        self._volume = _sugarext.VolumeAlsa()

    def get_muted(self):
        return self._volume.get_mute()

    def get_volume(self):
        return self._volume.get_volume()

    def set_volume(self, new_volume):
        old_volume = self._volume.get_volume()
        self._volume.set_volume(new_volume)

        self.emit('volume-changed', old_volume, new_volume)

    def set_muted(self, new_state):
        old_state = self._volume.get_mute()
        self._volume.set_mute(new_state)

        self.emit('muted-changed', old_state, new_state)

    def startup(self):
        if env.is_emulator() is False:
            profile = get_profile()
            self.set_volume(profile.sound_volume)

    def shutdown(self):
        if env.is_emulator() is False:
            profile = get_profile()
            profile.sound_volume = self.get_volume()
            profile.save()

    def set_dcon_freeze(self, frozen):
        try:
            self._service.SetKey("display.dcon_freeze", frozen)
        except dbus.DBusException:
            logging.error('Cannot unfreeze the DCON')

    def set_display_mode(self, mode):
        try:
            self._service.SetKey("display.dcon_mode", mode)
        except dbus.DBusException:
            logging.error('Cannot change DCON mode')

    def set_display_brightness(self, level):
        try:
            self._service.SetKey("backlight.hardware_brightness", level)
        except dbus.DBusException:
            logging.error('Cannot set display brightness')

    def get_display_brightness(self):
        try:
            return self._service.GetKey("backlight.hardware_brightness")
        except dbus.DBusException:
            logging.error('Cannot get display brightness')
            return 0

def get_manager():
    return _manager

def get_network_manager():
    return _network_manager

_manager = HardwareManager()

try:
    _network_manager = NMClient()
except dbus.DBusException, e:
    _network_manager = None
    logging.info('Network manager service not found.')
