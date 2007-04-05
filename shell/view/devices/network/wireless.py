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

from sugar.graphics import canvasicon
from sugar.graphics import color
from sugar.graphics import units
from model.devices.network import wireless
from sugar.graphics.canvasicon import CanvasIcon
from model.devices import device

_ICON_NAME = 'device-network-wireless'

class DeviceView(CanvasIcon):
    def __init__(self, model):
        CanvasIcon.__init__(self, scale=units.MEDIUM_ICON_SCALE)
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
        icon_name = canvasicon.get_icon_state(
                    _ICON_NAME, self._model.props.strength)
        if icon_name:
            self.props.icon_name = icon_name

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        if state == device.STATE_ACTIVATING:
            self.props.fill_color = color.ICON_FILL_INACTIVE
            self.props.stroke_color = color.ICON_STROKE_INACTIVE
        elif state == device.STATE_ACTIVATED:
            self.props.fill_color = None
            self.props.stroke_color = None
        elif state == device.STATE_INACTIVE:
            self.props.fill_color = color.ICON_FILL_INACTIVE
            self.props.stroke_color = color.ICON_STROKE_INACTIVE
