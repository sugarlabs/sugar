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

from jarabe.model.devices import device

def freq_to_channel(freq):
    ftoc = { 2.412: 1, 2.417: 2, 2.422: 3, 2.427: 4,
	     2.432: 5, 2.437: 6, 2.442: 7, 2.447: 8,
	     2.452: 9, 2.457: 10, 2.462: 11, 2.467: 12,
	     2.472: 13
	     }
    return ftoc[freq]

def channel_to_freq(channel):
    ctof = { 1: 2.412, 2: 2.417, 3: 2.422, 4: 2.427,
	     5: 2.432, 6: 2.437, 7: 2.442, 8: 2.447,
	     9: 2.452, 10: 2.457, 11: 2.462, 12: 2.467,
	     13: 2.472
	     }
    return ctof[channel]

class Device(device.Device):
    __gproperties__ = {
        'name'     : (str, None, None, None,
                      gobject.PARAM_READABLE),
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE),
        'state'    : (int, None, None, device.STATE_ACTIVATING,
                      device.STATE_INACTIVE, 0, gobject.PARAM_READABLE),
        'frequency': (float, None, None, 0.0, 9999.99, 0.0,
                      gobject.PARAM_READABLE)
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
            import logging
            logging.debug('wireless.Device.props.name: %s' %
                    self._nm_device.get_ssid())
            return self._nm_device.get_ssid()
        elif pspec.name == 'state':
            nm_state = self._nm_device.get_state()
            return device.nm_state_to_state[nm_state]
        elif pspec.name == 'frequency':
            return self._nm_device.get_frequency()

    def get_type(self):
        return 'wireless'

    def get_id(self):
        return str(self._nm_device.get_op())

    def get_active_network_colors(self):
        net = self._nm_device.get_active_network()
        if not net:
            return (None, None)
        return net.get_colors()

