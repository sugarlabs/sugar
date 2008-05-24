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

from hardware import nmclient

STATE_CONNECTING   = 0
STATE_CONNECTED    = 1
STATE_NOTCONNECTED = 2

_nm_state_to_state = {
    nmclient.NETWORK_STATE_CONNECTED    : STATE_CONNECTED,
    nmclient.NETWORK_STATE_CONNECTING   : STATE_CONNECTING,
    nmclient.NETWORK_STATE_NOTCONNECTED : STATE_NOTCONNECTED
}

class AccessPointModel(gobject.GObject):
    __gproperties__ = {
        'name'     : (str, None, None, None,
                      gobject.PARAM_READABLE),
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE),
        'state'    : (int, None, None, STATE_CONNECTING,
                      STATE_NOTCONNECTED, 0, gobject.PARAM_READABLE),
        'capabilities' : (int, None, None, 0, 0x7FFFFFFF, 0,
                      gobject.PARAM_READABLE),
        'mode'     : (int, None, None, 0, 6, 0, gobject.PARAM_READABLE)
    }

    def __init__(self, nm_device, nm_network):
        gobject.GObject.__init__(self)
        self._nm_network = nm_network
        self._nm_device = nm_device

        self._nm_network.connect('strength-changed',
                                 self._strength_changed_cb)
        self._nm_network.connect('state-changed',
                                 self._state_changed_cb)

    def _strength_changed_cb(self, nm_network):
        self.notify('strength')

    def _state_changed_cb(self, nm_network):
        self.notify('state')

    def get_id(self):
        return self._nm_network.get_op()

    def get_nm_device(self):
        return self._nm_device

    def get_nm_network(self):
        return self._nm_network

    def do_get_property(self, pspec):
        if pspec.name == 'strength':
            return self._nm_network.get_strength()
        elif pspec.name == 'name':
            return self._nm_network.get_ssid()
        elif pspec.name == 'state':
            nm_state = self._nm_network.get_state()
            return _nm_state_to_state[nm_state]
        elif pspec.name == 'capabilities':
            return self._nm_network.get_caps()
        elif pspec.name == 'mode':
            return self._nm_network.get_mode()
