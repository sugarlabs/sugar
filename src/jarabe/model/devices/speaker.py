# Copyright (C) 2008 Martin Dengler
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

import gobject

from jarabe.model import sound
from jarabe.model.devices import device

class Device(device.Device):
    __gproperties__ = {
        'level'   : (int, None, None, 0, 100, 0, gobject.PARAM_READWRITE),
        'muted'   : (bool, None, None, False, gobject.PARAM_READWRITE),
    }

    def __init__(self):
        device.Device.__init__(self)

        sound.muted_changed.connect(self.__muted_changed_cb)
        sound.volume_changed.connect(self.__volume_changed_cb)

    def __muted_changed_cb(self):
        self.notify('muted')

    def __volume_changed_cb(self):
        self.notify('level')

    def _get_level(self):
        return sound.get_volume()

    def _set_level(self, new_volume):
        self.sound.set_volume(new_volume)

    def _get_muted(self):
        return self.sound.get_muted()

    def _set_muted(self, mute):
        self.sound.set_muted(mute)

    def get_type(self):
        return 'speaker'

    def do_get_property(self, pspec):
        if pspec.name == "level":
            return self._get_level()
        elif pspec.name == "muted":
            return self._get_muted()

    def do_set_property(self, pspec, value):
        if pspec.name == "level":
            self._set_level(value)
        elif pspec.name == "muted":
            self._set_muted(value)
