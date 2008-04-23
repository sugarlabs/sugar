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

from gettext import gettext as _

import gtk

from sugar import profile
from sugar.graphics import style
from sugar.graphics.icon import get_icon_state
from sugar.graphics.tray import TrayIcon
from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor

from view.frame.frameinvoker import FrameWidgetInvoker

_ICON_NAME = 'battery'

_STATUS_CHARGING = 0
_STATUS_DISCHARGING = 1
_STATUS_FULLY_CHARGED = 2

class DeviceView(TrayIcon):
    def __init__(self, model):
        TrayIcon.__init__(self, icon_name=_ICON_NAME,
                          xo_color=profile.get_color())

        self._model = model
        self.palette = BatteryPalette(_('My Battery'))
        self.set_palette(self.palette)
        self.palette.props.invoker = FrameWidgetInvoker(self)
        self.palette.set_group_id('frame')

        model.connect('notify::level', self._battery_status_changed_cb)
        model.connect('notify::charging', self._battery_status_changed_cb)
        model.connect('notify::discharging', self._battery_status_changed_cb)
        self._update_info()

    def _update_info(self):
        name = _ICON_NAME
        current_level = self._model.props.level
        xo_color = profile.get_color()
        badge_name = None

        if self._model.props.charging:
            status = _STATUS_CHARGING
            name += '-charging'
            xo_color = XoColor('%s,%s' % (style.COLOR_WHITE.get_svg(),
                                          style.COLOR_WHITE.get_svg()))
        elif self._model.props.discharging:
            status = _STATUS_DISCHARGING
            if current_level <= 15:
                badge_name = 'emblem-warning'
        else:
            status = _STATUS_FULLY_CHARGED

        self.icon.props.icon_name = get_icon_state(name, current_level)
        self.icon.props.xo_color = xo_color
        self.icon.props.badge_name = badge_name

        self.palette.set_level(current_level)
        self.palette.set_status(status)

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
        fraction = percent / 100.0
        self._progress_bar.set_fraction(fraction)

    def set_status(self, status):
        current_level = self._level
        secondary_text = ''
        status_text = '%s%%' % current_level

        if status == _STATUS_CHARGING:
            secondary_text = _('Charging')
        elif status == _STATUS_DISCHARGING:
            if current_level <= 15:
                secondary_text = _('Very little power remaining')
            else:
                #TODO: make this less of an wild/educated guess
                minutes_remaining = int(current_level / 0.59)
                remaining_hourpart = minutes_remaining / 60
                remaining_minpart = minutes_remaining % 60
                secondary_text = _('%(hour)d:%(min).2d remaining'
                                   % { 'hour': remaining_hourpart,
                                       'min': remaining_minpart})
        else:
            secondary_text = _('Charged')
            status_text = ''

        self.props.secondary_text = secondary_text
        self._status_label.set_text(status_text)
