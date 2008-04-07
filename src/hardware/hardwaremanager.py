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
import gst
import gst.interfaces

from hardware.nmclient import NMClient
from sugar.profile import get_profile
from sugar import env

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
        except dbus.DBusException, e:
            self._service = None
            logging.info('Hardware manager service not found.')

        self._mixer = gst.element_factory_make('alsamixer')
        self._mixer.set_state(gst.STATE_PAUSED)

        self._master = None
        for track in self._mixer.list_tracks():
            if track.flags & gst.interfaces.MIXER_TRACK_MASTER:
                self._master = track

    def get_volume(self):
        if not self._mixer or not self._master:
            logging.error('Cannot get the volume')
            return self._convert_volume(0)

        max_volume = self._master.max_volume
        min_volume = self._master.min_volume
        volume = self._mixer.get_volume(self._master)[0]

        return volume * 100.0 / (max_volume - min_volume) + min_volume

    def set_volume(self, volume):
        if not self._mixer or not self._master:
            logging.error('Cannot set the volume')
            return

        if volume < 0 or volume > 100:
            logging.error('Trying to set an invalid volume value.')
            return

        max_volume = self._master.max_volume
        min_volume = self._master.min_volume

        volume = volume * (max_volume - min_volume) / 100.0 + min_volume
        volume_list = [ volume ] * self._master.num_channels

        self._mixer.set_volume(self._master, tuple(volume_list))

    def set_mute(self, mute):
        if not self._mixer or not self._master:
            logging.error('Cannot mute the audio channel')
        self._mixer.set_mute(self._master, mute)

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
        if not self._service:
            return

        self._service.set_dcon_freeze(frozen)

    def set_display_mode(self, mode):
        if not self._service:
            return

        self._service.set_display_mode(mode)

    def set_display_brightness(self, level):
        if not self._service:
            logging.error('Cannot set display brightness')
            return

        self._service.set_display_brightness(level)

    def get_display_brightness(self):
        if not self._service:
            logging.error('Cannot get display brightness')
            return

        return self._service.get_display_brightness()

    def toggle_keyboard_brightness(self):
        if not self._service:
            return

        if self._service.get_keyboard_brightness():
            self._service.set_keyboard_brightness(False)
        else:
            self._service.set_keyboard_brightness(True)            

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
