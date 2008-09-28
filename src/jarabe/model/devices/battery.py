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

import logging

import gobject
import dbus

from jarabe.model.devices import device

_LEVEL_PROP = 'battery.charge_level.percentage'
_CHARGING_PROP = 'battery.rechargeable.is_charging'
_DISCHARGING_PROP = 'battery.rechargeable.is_discharging'

class Device(device.Device):
    __gproperties__ = {
        'level'       : (int, None, None, 0, 100, 0,
                         gobject.PARAM_READABLE),
        'charging'    : (bool, None, None, False,
                         gobject.PARAM_READABLE),
        'discharging' : (bool, None, None, False,
                         gobject.PARAM_READABLE)
    }

    def __init__(self, udi):
        device.Device.__init__(self, udi)
        
        bus = dbus.Bus(dbus.Bus.TYPE_SYSTEM)
        proxy = bus.get_object('org.freedesktop.Hal', udi,
                               follow_name_owner_changes=True)
        self._battery = dbus.Interface(proxy, 'org.freedesktop.Hal.Device')
        bus.add_signal_receiver(self._battery_changed,
                                'PropertyModified',
                                'org.freedesktop.Hal.Device',
                                'org.freedesktop.Hal',
                                udi)

        self._level = self._get_level()
        self._charging = self._get_charging()
        self._discharging = self._get_discharging()

    def _get_level(self):
        try:
            return self._battery.GetProperty(_LEVEL_PROP)
        except dbus.DBusException:
            logging.error('Cannot access %s' % _LEVEL_PROP)
            return 0

    def _get_charging(self):
        try:
            return self._battery.GetProperty(_CHARGING_PROP)
        except dbus.DBusException:
            logging.error('Cannot access %s' % _CHARGING_PROP)
            return False

    def _get_discharging(self):
        try:
            return self._battery.GetProperty(_DISCHARGING_PROP)
        except dbus.DBusException:
            logging.error('Cannot access %s' % _DISCHARGING_PROP)
            return False

    def do_get_property(self, pspec):
        if pspec.name == 'level':
            return self._level 
        if pspec.name == 'charging':
            return self._charging
        if pspec.name == 'discharging':
            return self._discharging

    def get_type(self):
        return 'battery'

    def _battery_changed(self, num_changes, changes_list):
        for change in changes_list:
            if change[0] == _LEVEL_PROP:
                self._level = self._get_level()
                self.notify('level')
            elif change[0] == _CHARGING_PROP:
                self._charging = self._get_charging()
                self.notify('charging')
            elif change[0] == _DISCHARGING_PROP:
                self._discharging = self._get_discharging()
                self.notify('discharging')
