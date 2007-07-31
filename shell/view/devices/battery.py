# Copyright (C) 2006-2007, Red Hat, Inc.
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

import gtk

from gettext import gettext as _
from sugar.graphics import canvasicon
from sugar.graphics import style
from sugar.graphics.palette import Palette

_ICON_NAME = 'device-battery'

_STATUS_CHARGING = 0
_STATUS_DISCHARGING = 1
_STATUS_FULLY_CHARGED = 2

class DeviceView(canvasicon.CanvasIcon):
    def __init__(self, model):
        canvasicon.CanvasIcon.__init__(self, size=style.MEDIUM_ICON_SIZE)
        self._model = model
        self._palette = BatteryPalette(_('My Battery life'))
        self.set_palette(self._palette)

        model.connect('notify::level', self._battery_status_changed_cb)
        model.connect('notify::charging', self._battery_status_changed_cb)
        model.connect('notify::discharging', self._battery_status_changed_cb)
        self._update_info()

    def _update_info(self):
        self.props.icon_name = canvasicon.get_icon_state(
                                    _ICON_NAME, self._model.props.level)

        # Update palette
        if self._model.props.charging:
            status = _STATUS_CHARGING
        elif self._model.props.discharging:
            status = _STATUS_DISCHARGING
        else:
            status = _STATUS_FULLY_CHARGED

        self._palette.set_level(self._model.props.level)
        self._palette.set_status(status)

    def _battery_status_changed_cb(self, pspec, param):
        self._update_info()

class BatteryPalette(Palette):

    def __init__(self, primary_text):
        Palette.__init__(self, primary_text)
            
        self._level = 0
        self._progress_bar = gtk.ProgressBar()
        self._progress_bar.show()
        self._status_label = gtk.Label()
        self._status_label.show()

        vbox = gtk.VBox()
        vbox.pack_start(self._progress_bar)
        vbox.pack_start(self._status_label)
        vbox.show()

        self.set_content(vbox)

    def set_level(self, percent):
        self._level = percent
        fraction = percent/100.0
        self._progress_bar.set_fraction(fraction)

    def set_status(self, status):
        percent_string = ' (%s%%)' % self._level

        if status == _STATUS_CHARGING:
            charge_text = _('Battery charging') + percent_string
        elif status == _STATUS_DISCHARGING:
            charge_text = _('Battery discharging') + percent_string
        elif status == _STATUS_FULLY_CHARGED:
            charge_text = _('Battery fully charged')

        self._status_label.set_text(charge_text)
