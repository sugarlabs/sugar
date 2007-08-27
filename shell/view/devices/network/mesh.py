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

from sugar import profile
from sugar.graphics import canvasicon
from sugar.graphics import style
from model.devices import device

class DeviceView(canvasicon.CanvasIcon):
    def __init__(self, model):
        canvasicon.CanvasIcon.__init__(self, size=style.MEDIUM_ICON_SIZE,
                                       icon_name='network-mesh')
        self._model = model

        model.connect('notify::state', self._state_changed_cb)
        self._update_state()

    def _state_changed_cb(self, model, pspec):
        self._update_state()

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        if state == device.STATE_ACTIVATING:
            self.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
        elif state == device.STATE_ACTIVATED:
            self.props.xo_color = profile.get_color()
        elif state == device.STATE_INACTIVE:
            self.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
