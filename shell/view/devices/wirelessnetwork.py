#
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

from view.devices import deviceview
from model.devices import wirelessnetwork

_strength_to_icon = {
    (0,   20) : 'stock-net-wireless-00',
    (21,  40) : 'stock-net-wireless-21-40',
    (41,  60) : 'stock-net-wireless-41-60',
    (61,  80) : 'stock-net-wireless-61-80',
    (81, 100) : 'stock-net-wireless-81-100'
}

class DeviceView(deviceview.DeviceView):
    def __init__(self, model):
        deviceview.DeviceView.__init__(self, model)
        self._model = model

        model.connect('notify::name', self._name_changed_cb)
        model.connect('notify::strength', self._strength_changed_cb)
        model.connect('notify::state', self._state_changed_cb)

        self._update_name()
        self._update_icon()
        self._update_state()

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()

    def _name_changed_cb(self, model, pspec):
        self._update_name()

    def _state_changed_cb(self, model, pspec):
        self._update_state()

    def _update_name(self):
        self.props.tooltip = self._model.props.name

    def _update_icon(self):
        strength = self._model.props.strength
        for interval in _strength_to_icon.keys():
            if strength >= interval[0] and strength <= interval[1]:
                stock_name = _strength_to_icon[interval]
                self.props.icon_name = 'theme:' + stock_name

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        if state == wirelessnetwork.STATE_ACTIVATING:
            self.props.background_color = 0xFF0000FF
        elif state == wirelessnetwork.STATE_ACTIVATED:
            self.props.background_color = 0x00FF00FF
        elif state == wirelessnetwork.STATE_INACTIVE:
            self.props.background_color = 0x00000000
