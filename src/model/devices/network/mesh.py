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

class Device(device.Device):
    __gproperties__ = {
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE),
        'state'    : (int, None, None, device.STATE_ACTIVATING,
                      device.STATE_INACTIVE, 0, gobject.PARAM_READABLE),
        'activation-stage': (int, None, None, 0, 7, 0, gobject.PARAM_READABLE),
        'frequency': (float, None, None, 0, 2.72, 0, gobject.PARAM_READABLE),
        'mesh-step': (int, None, None, 0, 4, 0, gobject.PARAM_READABLE),
        'ip-address' : (str, None, None, None, gobject.PARAM_READABLE),
    }

    def __init__(self, nm_device):
        device.Device.__init__(self)
        self._nm_device = nm_device
        self._nm_device.connect('ip-changed', self._ip_changed_cb)
        self.notify('ip-address')

        self._nm_device.connect('strength-changed',
                                self._strength_changed_cb)
        self._nm_device.connect('state-changed',
                                self._state_changed_cb)
        self._nm_device.connect('activation-stage-changed',
                                self._activation_stage_changed_cb)

    def _strength_changed_cb(self, nm_device):
        self.notify('strength')

    def _state_changed_cb(self, nm_device):
        self.notify('state')

    def _ip_changed_cb(self, nm_device):
        self.notify('ip-address')

    def _activation_stage_changed_cb(self, nm_device):
        self.notify('activation-stage')

    def do_get_property(self, pspec):
        if pspec.name == 'strength':
            return self._nm_device.get_strength()
        elif pspec.name == 'state':
            nm_state = self._nm_device.get_state()
            return device.nm_state_to_state[nm_state]
        elif pspec.name == 'activation-stage':
            return self._nm_device.get_activation_stage()
        elif pspec.name == 'frequency':
            return self._nm_device.get_frequency()
        elif pspec.name == 'mesh-step':
            return self._nm_device.get_mesh_step()
        elif pspec.name == 'ip-address':
            return self.get_ip_address()

    def get_ip_address(self):
        if self._nm_device is not None:
            return self._nm_device.get_ip_address()

    def get_type(self):
        return 'network.mesh'

    def get_id(self):
        return str(self._nm_device.get_op())

    def get_nm_device(self):
        return self._nm_device

