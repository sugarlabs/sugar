# Copyright (C) 2006-2007, Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gettext import gettext as _

import gi
gi.require_version('UPowerGlib', '1.0')

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import UPowerGlib
import dbus
import time

import logging

from sugar3 import profile
from sugar3.graphics import style
from sugar3.graphics.icon import get_icon_state
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model.session import get_session_manager


_ICON_NAME = 'battery'

_STATUS_CHARGING = 0
_STATUS_DISCHARGING = 1
_STATUS_FULLY_CHARGED = 2
_STATUS_NOT_PRESENT = 3

_UP_DEVICE_IFACE = 'org.freedesktop.UPower.Device'

_UP_TYPE_BATTERY = 2

_settings = None
_warning_capacity = 15


def _settings_get(key):
    global _settings

    if _settings is None:
        _settings = Gio.Settings('org.sugarlabs.power')

    return _settings.get_double(key)


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 102

    def __init__(self, battery):
        self._color = profile.get_color()

        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)

        self.set_palette_invoker(FrameWidgetInvoker(self))

        self._model = DeviceModel(battery)
        self.palette = BatteryPalette(_('My Battery'))
        self.palette.set_group_id('frame')
        self.palette_invoker.props.toggle_palette = True
        self._model.connect('updated',
                            self.__battery_status_changed_cb)
        self._update_info()

    def _update_info(self):
        name = _ICON_NAME
        current_level = self._model.props.level
        xo_color = self._color
        badge_name = None
        self.show()

        if not self._model.props.present:
            self.hide()
            status = _STATUS_NOT_PRESENT

        elif self._model.props.charging:
            status = _STATUS_CHARGING
            name += '-charging'

        elif self._model.props.discharging:
            status = _STATUS_DISCHARGING
            if current_level <= self._model.warning_capacity:
                badge_name = 'emblem-warning'
        else:
            status = _STATUS_FULLY_CHARGED

        if self._model.props.present:
            self.icon.props.icon_name = get_icon_state(name, current_level,
                                                       step=-5)
            self.icon.props.xo_color = xo_color
            self.icon.props.badge_name = badge_name

        self.palette.set_info(current_level, self._model.props.time_remaining,
                              status)

    def __battery_status_changed_cb(self, model):
        self._update_info()


class BatteryPalette(Palette):

    def __init__(self, primary_text):
        Palette.__init__(self, primary_text)
        self._level = 0
        self._time = 0
        self._status = _STATUS_NOT_PRESENT
        self._warning_capacity = _settings_get('warning-capacity')

        self._progress_widget = PaletteMenuBox()
        self.set_content(self._progress_widget)
        self._progress_widget.show()

        inner_box = Gtk.VBox()
        inner_box.set_spacing(style.DEFAULT_PADDING)
        self._progress_widget.append_item(inner_box, vertical_padding=0)
        inner_box.show()

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_size_request(
            style.zoom(style.GRID_CELL_SIZE * 4), -1)
        inner_box.pack_start(self._progress_bar, True, True, 0)
        self._progress_bar.show()

        self._status_label = Gtk.Label()
        inner_box.pack_start(self._status_label, True, True, 0)
        self._status_label.show()

    def set_info(self, percentage, seconds, status):
        self._level = percentage
        self._time = seconds
        self._status = status
        self._progress_bar.set_fraction(percentage / 100.0)
        self._update_secondary()

    def _update_secondary(self):
        secondary_text = ''
        status_text = '%s%%' % (self._level, )

        progress_widget = self._progress_widget
        if self._status == _STATUS_NOT_PRESENT:
            secondary_text = _('Removed')
            progress_widget = None
        elif self._status == _STATUS_CHARGING:
            secondary_text = _('Charging')
        elif self._status == _STATUS_DISCHARGING:
            if self._level <= self._warning_capacity:
                secondary_text = _('Very little power remaining')
            else:
                minutes_remaining = self._time // 60
                remaining_hourpart = minutes_remaining // 60
                remaining_minpart = minutes_remaining % 60
                # TRANS: do not translate %(hour)d:%(min).2d  it is a variable,
                # only translate the word "remaining"
                secondary_text = _('%(hour)d:%(min).2d remaining') % \
                    {'hour': remaining_hourpart, 'min': remaining_minpart}
        else:
            secondary_text = _('Charged')

        self.set_content(progress_widget)

        self.props.secondary_text = secondary_text
        self._status_label.set_text(status_text)


class DeviceModel(GObject.GObject):
    __gproperties__ = {
        'level': (int, None, None, 0, 100, 0, GObject.PARAM_READABLE),
        'time-remaining': (int, None, None, 0, GLib.MAXINT32, 0,
                           GObject.PARAM_READABLE),  # unit: seconds
        'charging': (bool, None, None, False, GObject.PARAM_READABLE),
        'discharging': (bool, None, None, False, GObject.PARAM_READABLE),
        'present': (bool, None, None, False, GObject.PARAM_READABLE),
    }

    __gsignals__ = {
        'updated': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, battery):
        GObject.GObject.__init__(self)
        self._battery = UPowerGlib.Device()
        self._battery.set_object_path_sync(battery, None)
        self._connect_battery()
        self._fetch_properties_from_upower()
        self._timeout_sid = False
        self.warning_capacity = _settings_get('warning-capacity')
        self._minimum_capacity = _settings_get('minimum-capacity')
        self._grace_time = _settings_get('grace-time')
        self._grace = time.time()

    def _connect_battery(self):
        """Connect to battery signals so we are told of changes."""

        if 'changed' not in GObject.signal_list_names(UPowerGlib.Device):
            # For UPower 0.99.4 and later
            self._battery.connect('notify::percentage', self.__notify_cb)
            self._battery.connect('notify::state', self.__notify_cb)
            self._battery.connect('notify::is-present', self.__notify_cb)
            self._battery.connect('notify::time-to-empty', self.__notify_cb)
            self._battery.connect('notify::time-to-full', self.__notify_cb)
        else:
            # For UPower 0.19.9
            self._battery.connect('changed', self.__notify_cb, None)

    def _fetch_properties_from_upower(self):
        """Get current values from UPower."""

        self._level = self._battery.props.percentage
        self._state = self._battery.props.state
        self._present = self._battery.props.is_present
        self._time_to_empty = self._battery.props.time_to_empty
        self._time_to_full = self._battery.props.time_to_full

    def do_get_property(self, pspec):
        """Return current value of given GObject property."""
        if pspec.name == 'level':
            return self._level
        if pspec.name == 'charging':
            return self._state == UPowerGlib.DeviceState.CHARGING
        if pspec.name == 'discharging':
            return self._state == UPowerGlib.DeviceState.DISCHARGING
        if pspec.name == 'present':
            return self._present
        if pspec.name == 'time-remaining':
            if self._state == UPowerGlib.DeviceState.CHARGING:
                return self._time_to_full
            if self._state == UPowerGlib.DeviceState.DISCHARGING:
                return self._time_to_empty
            return 0

    def get_type(self):
        return 'battery'

    def __notify_cb(self, device, name):
        """Defer response to notifications; they arrive in a burst,
        but without any indication that the burst is complete, so we
        use a timeout to respond."""
        if self._timeout_sid:
            GObject.source_remove(self._timeout_sid)
        self._timeout_sid = GObject.timeout_add(100, self.__timeout_cb)

    def __timeout_cb(self):
        old_level = self._level
        old_state = self._state
        old_present = self._present
        old_time = self.props.time_remaining
        self._fetch_properties_from_upower()
        if self._level != old_level:
            self.notify('level')
        if self._state != old_state:
            self.notify('charging')
            self.notify('discharging')
        if self._present != old_present:
            self.notify('present')
        if self.props.time_remaining != old_time:
            self.notify('time-remaining')

        self.emit('updated')
        self._timeout_sid = None
        self.__check_capacity()
        return False

    def __check_capacity(self):
        if self._state != UPowerGlib.DeviceState.DISCHARGING:
            return

        if self._level > self.warning_capacity:
            return

        if self._level > self._minimum_capacity:
            logging.error('battery under warning, %d%%' % self._level)
            return

        elapsed = time.time() - self._grace
        if elapsed < self._grace_time:
            logging.error('battery under minimum, %d%%, grace %d%%' %
                          (self._level, elapsed * 100 / self._grace))
            return

        logging.error('battery under minimum, %d%%, forced shutdown' %
                      self._level)
        sm = get_session_manager()
        sm.shutdown()
        GObject.timeout_add_seconds(10, sm.shutdown_completed)

def setup(tray):
    bus = dbus.Bus(dbus.Bus.TYPE_SYSTEM)
    up_proxy = bus.get_object('org.freedesktop.UPower',
                              '/org/freedesktop/UPower')
    upower = dbus.Interface(up_proxy, 'org.freedesktop.UPower')

    for device_path in upower.EnumerateDevices():
        device = bus.get_object('org.freedesktop.UPower', device_path)
        device_prop_iface = dbus.Interface(device, dbus.PROPERTIES_IFACE)
        device_type = device_prop_iface.Get(_UP_DEVICE_IFACE, 'Type')
        if device_type == _UP_TYPE_BATTERY:
            tray.add_device(DeviceView(device_path))
