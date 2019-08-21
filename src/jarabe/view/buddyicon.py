# Copyright (C) 2006-2007 Red Hat, Inc.
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

import gi
gi.require_version('UPowerGlib', '1.0')
from gi.repository import GObject
from gi.repository import UPowerGlib
from gi.repository import Gio
from gi.repository import GLib

from sugar3.graphics import style
from sugar3.graphics.icon import CanvasIcon
from sugar3 import env
from sugar3.datastore import datastore

from jarabe.view.buddymenu import BuddyMenu
from jarabe.util.normalize import normalize_string
from jarabe.model.session import get_session_manager
from jarabe import config

import os
import statvfs
import time
import dbus

_FILTERED_ALPHA = 0.33
_UP_TYPE_BATTERY = 2
_UP_DEVICE_IFACE = 'org.freedesktop.UPower.Device'

_settings = None


class BuddyIcon(CanvasIcon):

    def __init__(self, buddy, pixel_size=style.STANDARD_ICON_SIZE):
        CanvasIcon.__init__(self, icon_name='computer-xo',
                            pixel_size=pixel_size)

        self._filtered = False
        self._buddy = buddy
        self._buddy.connect('notify::present', self.__buddy_notify_present_cb)
        self._buddy.connect('notify::color', self.__buddy_notify_color_cb)

        self.palette_invoker.props.toggle_palette = True
        self.palette_invoker.cache_palette = False

        self._update_color()

        settings = Gio.Settings('org.sugarlabs')
        variable_apr = settings.get_boolean('variable-buddy-icon')

        if variable_apr:
            self.icon_dict = {'embryo': {'normal': 'embryo-test',
                                     'disk_50': 'embryo-disk50',
                                     'disk_90': 'embryo-disk90'},
                          'teen': {'normal': 'teen',
                                   'disk_50': 'teen-disk50',
                                   'disk_90': 'teen-disk90'},
                          'adult': {'normal': 'computer-xo',
                                    'disk_50': 'adult-disk50',
                                    'disk_90': 'adult-disk90'}
                          }
            self.journal_entries = 0
            self.has_battery = None    
            self.__tamagotchi_thread()
            
    def __tamagotchi_thread(self):
        GLib.timeout_add(60000, self.__tamagotchi_thread)
        self.__datastore_query()

        user_type = None
        disk_space_type = None
        _, self.total, self.used = self._get_space()

        if self.journal_entries <= 10:
            user_type = 'embryo'
        elif self.journal_entries > 10 and self.journal_entries <= 50:
            user_type = 'teen'
        elif self.journal_entries >= 50:
            user_type = 'adult'

        diskspace_50 = int(self.total / 2)
        diskspace_90 = int((90 * self.total) / 100)

        if self.used > diskspace_90:
            disk_space_type = 'disk_90'
        elif self.used > diskspace_50:
            disk_space_type = 'disk_50'
        else:
            disk_space_type = 'normal'

        self.set_icon_name(self.icon_dict[user_type][disk_space_type])
        self.__get_battery()
        self.__status_tooltip(self.has_battery)

    def __get_battery(self):
        bus = dbus.Bus(dbus.Bus.TYPE_SYSTEM)
        up_proxy = bus.get_object('org.freedesktop.UPower',
                                  '/org/freedesktop/UPower')
        upower = dbus.Interface(up_proxy, 'org.freedesktop.UPower')

        for device_path in upower.EnumerateDevices():
            device = bus.get_object('org.freedesktop.UPower', device_path)
            device_prop_iface = dbus.Interface(device, dbus.PROPERTIES_IFACE)
            device_type = device_prop_iface.Get(_UP_DEVICE_IFACE, 'Type')
            battery = None
            if device_type == _UP_TYPE_BATTERY:
                battery = DeviceModel(device_path)
                self.level = battery.props.level
                self.has_battery = battery.props.present

            if self.has_battery:
                if self.level == 100:
                    icon_name = 'battery-100'
                else:
                    icon_name = 'battery-0' + str(int(self.level / 10)) + '0'
                self.props.badge_name = icon_name

    def __status_tooltip(self, has_battery=False):
        disk_usage = (self.used * 100) / self.total
        battery = ''
        if has_battery:
            battery = "\n{} Battery".format(str(self.level))
        tooltip_str = "{}% Disk space used {}".format(str(disk_usage), battery)
        self.set_tooltip_text(tooltip_str)

    def __datastore_query(self):
        _, entries = datastore.find({})
        self.journal_entries = entries

    def _get_space(self):
        stat = os.statvfs(env.get_profile_path())
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        free_space = self._get_MBs(free_space)
        total_space = self._get_MBs(total_space)
        used_space = total_space - free_space

        return free_space, total_space, used_space

    def _get_MBs(self, space):
        space = space / (1024 * 1024)
        return space

    def create_palette(self):
        palette = BuddyMenu(self._buddy)
        self.connect_to_palette_pop_events(palette)
        return palette

    def __buddy_notify_present_cb(self, buddy, pspec):
        # Update the icon's color when the buddy comes and goes
        self._update_color()

    def __buddy_notify_color_cb(self, buddy, pspec):
        self._update_color()

    def _update_color(self):
        # keep the icon in the palette in sync with the view
        palette = self.get_palette()
        self.props.xo_color = self._buddy.get_color()
        if self._filtered:
            self.alpha = _FILTERED_ALPHA
            if palette is not None:
                palette.props.icon.props.stroke_color = self.props.stroke_color
                palette.props.icon.props.fill_color = self.props.fill_color
        else:
            self.alpha = 1.0
            if palette is not None:
                palette.props.icon.props.xo_color = self._buddy.get_color()

    def set_filter(self, query):
        normalized_name = normalize_string(
            self._buddy.get_nick().decode('utf-8'))
        self._filtered = (normalized_name.find(query) == -1) \
            and not self._buddy.is_owner()
        self._update_color()

    def get_positioning_data(self):
        return self._buddy.get_key()


class DeviceModel(GObject.GObject):
    __gproperties__ = {
        'level': (int, None, None, 0, 100, 0, GObject.ParamFlags.READABLE),
        'time-remaining': (int, None, None, 0, GLib.MAXINT32, 0,
                           GObject.ParamFlags.READABLE),  # unit: seconds
        'charging': (bool, None, None, False, GObject.ParamFlags.READABLE),
        'discharging': (bool, None, None, False, GObject.ParamFlags.READABLE),
        'present': (bool, None, None, False, GObject.ParamFlags.READABLE),
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
            GLib.source_remove(self._timeout_sid)
        self._timeout_sid = GLib.timeout_add(100, self.__timeout_cb)

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
        return False

        sm = get_session_manager()
        sm.shutdown()
        GLib.timeout_add_seconds(10, sm.shutdown_completed)


def _settings_get(key):
    global _settings

    if _settings is None:
        _settings = Gio.Settings('org.sugarlabs.power')

    return _settings.get_double(key)
