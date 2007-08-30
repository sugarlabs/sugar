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

from gettext import gettext as _

import gtk

from sugar.graphics.icon import get_icon_state
from sugar.graphics.icon import CanvasIcon
from sugar.graphics import style
from sugar.graphics.palette import Palette

from model.devices.network import wireless
from model.devices import device

_ICON_NAME = 'network-wireless'

class DeviceView(CanvasIcon):
    def __init__(self, model):
        CanvasIcon.__init__(self, size=style.MEDIUM_ICON_SIZE)
        self._model = model
        self._palette = WirelessPalette(self._get_palette_primary_text())
        self.set_palette(self._palette)
        self._counter = 0
        self._palette.set_frequency(self._model.props.frequency)

        model.connect('notify::name', self._name_changed_cb)
        model.connect('notify::strength', self._strength_changed_cb)
        model.connect('notify::state', self._state_changed_cb)

        self._update_icon()
        self._update_state()

    def _get_palette_primary_text(self):
        if self._model.props.state == device.STATE_INACTIVE:
            return _("Disconnected")
        return self._model.props.name

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()
        # Only update frequency periodically
        if self._counter % 4 == 0:
            self._palette.set_frequency(self._model.props.frequency)
        self._counter += 1

    def _name_changed_cb(self, model, pspec):
        self.palette.set_primary_text(self._get_palette_primary_text())

    def _state_changed_cb(self, model, pspec):
        self._update_state()
        self.palette.set_primary_text(self._get_palette_primary_text())

    def _update_icon(self):
        strength = self._model.props.strength
        if self._model.props.state == device.STATE_INACTIVE:
            strength = 0
        icon_name = get_icon_state(_ICON_NAME, strength)
        if icon_name:
            self.props.icon_name = icon_name

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        if state == device.STATE_ACTIVATING:
            self.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
        elif state == device.STATE_ACTIVATED:
            (stroke, fill) = self._model.get_active_network_colors()
            self.props.stroke_color = stroke
            self.props.fill_color = fill
        elif state == device.STATE_INACTIVE:
            self.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()

class WirelessPalette(Palette):
    def __init__(self, primary_text):
        Palette.__init__(self, primary_text)

        self._chan_label = gtk.Label()
        self._chan_label.show()

        vbox = gtk.VBox()
        vbox.pack_start(self._chan_label)
        vbox.show()

        self.set_content(vbox)

    def set_frequency(self, freq):
        chans = { 2.412: 1, 2.417: 2, 2.422: 3, 2.427: 4,
                  2.432: 5, 2.437: 6, 2.442: 7, 2.447: 8,
                  2.452: 9, 2.457: 10, 2.462: 11, 2.467: 12,
                  2.472: 13
                }
        try:
            chan = chans[freq]
        except KeyError:
            chan = 0
        self._chan_label.set_text("%s: %d" % (_("Channel"), chan))

