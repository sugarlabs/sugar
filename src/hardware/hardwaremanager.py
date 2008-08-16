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
import gst
import gst.interfaces

from hardware.nmclient import NMClient
from sugar.profile import get_profile
from sugar import env

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

        self._mixer = gst.element_factory_make('alsamixer')
        self._mixer.set_state(gst.STATE_PAUSED)

        self._master = None
        for track in self._mixer.list_tracks():
            if track.flags & gst.interfaces.MIXER_TRACK_MASTER:
                self._master = track

    def __muted_changed_cb(self, old_state, new_state):
        if old_state != new_state:
            self.emit('muted-changed', old_state, new_state)

    def __volume_changed_cb(self, old_volume, new_volume):
        if old_volume != new_volume:
            self.emit('volume-changed', old_volume, new_volume)

    def get_muted(self):
        if not self._mixer or not self._master:
            logging.error('Cannot get the mute status')
            return True
        return self._master.flags & gst.interfaces.MIXER_TRACK_MUTE \
                 == gst.interfaces.MIXER_TRACK_MUTE

    def get_volume(self):
        if not self._mixer or not self._master:
            logging.error('Cannot get the volume')
            return 0

        max_volume = self._master.max_volume
        min_volume = self._master.min_volume

        volumes = self._mixer.get_volume(self._master)

        #sometimes we get a spurious zero from one/more channel(s)
        #TODO: consider removing this when trac #6933 is resolved
        nonzero_volumes = [v for v in volumes if v > 0]

        if len(nonzero_volumes) > 0:
            #we could just pick the first nonzero volume, but this converges
            volume = sum(nonzero_volumes) / len(nonzero_volumes)
            return volume * 100.0 / (max_volume - min_volume) + min_volume
        else:
            return 0

    def set_volume(self, new_volume):
        if not self._mixer or not self._master:
            logging.error('Cannot set the volume')
            return

        if new_volume < 0 or new_volume > 100:
            logging.error('Trying to set an invalid volume value.')
            return

        old_volume = self.get_volume()
        max_volume = self._master.max_volume
        min_volume = self._master.min_volume

        new_volume_mixer_range = min_volume + \
            (new_volume * ((max_volume - min_volume) / 100.0))
        volume_list = [ new_volume_mixer_range ] * self._master.num_channels

        #sometimes alsa sets one/more channels' volume to zero instead
        # of what we asked for, so try a few times
        #TODO: consider removing this loop when trac #6934 is resolved
        last_volumes_read = [0]
        read_count = 0
        while (0 in last_volumes_read) and (read_count < 3):
            self._mixer.set_volume(self._master, tuple(volume_list))
            last_volumes_read = self._mixer.get_volume(self._master)
            read_count += 1

        self.emit('volume-changed', old_volume, new_volume)

    def set_muted(self, new_state):
        if not self._mixer or not self._master:
            logging.error('Cannot mute the audio channel')
            return
        old_state = self.get_muted()
        self._mixer.set_mute(self._master, new_state)
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
