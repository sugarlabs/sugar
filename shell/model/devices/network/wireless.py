#
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

import gobject

from model.devices import device
from hardware import nmclient

class Device(device.Device):
    __gproperties__ = {
        'name'     : (str, None, None, None,
                      gobject.PARAM_READABLE),
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE),
        'state'    : (int, None, None, device.STATE_ACTIVATING,
                      device.STATE_INACTIVE, 0, gobject.PARAM_READABLE)
    }

    def __init__(self, nm_device):
        device.Device.__init__(self)
        self._nm_device = nm_device

        self._nm_device.connect('strength-changed',
                                self._strength_changed_cb)
        self._nm_device.connect('ssid-changed',
                                self._ssid_changed_cb)
        self._nm_device.connect('state-changed',
                                self._state_changed_cb)

    def _strength_changed_cb(self, nm_device):
        self.notify('strength')

    def _ssid_changed_cb(self, nm_device):
        self.notify('name')

    def _state_changed_cb(self, nm_device):
        self.notify('state')

    def do_get_property(self, pspec):
        if pspec.name == 'strength':
            return self._nm_device.get_strength()
        elif pspec.name == 'name':
            return self._nm_device.get_ssid()
        elif pspec.name == 'state':
            nm_state = self._nm_device.get_state()
            return device._nm_state_to_state[nm_state]

    def get_type(self):
        return 'network.wireless'

    def get_id(self):
        return str(self._nm_device.get_op())
