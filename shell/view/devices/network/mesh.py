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

from sugar.graphics import canvasicon
from sugar.graphics import color
from sugar.graphics import units
from model.devices import device

class DeviceView(canvasicon.CanvasIcon):
    def __init__(self, model):
        canvasicon.CanvasIcon.__init__(self, scale=units.MEDIUM_ICON_SCALE,
                icon_name='theme:device-network-mesh')
        self._model = model

        model.connect('notify::state', self._state_changed_cb)
        self._update_state()

    def _state_changed_cb(self, model, pspec):
        self._update_state()

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
