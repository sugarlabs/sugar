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

import gobject
import dbus

from model.devices import device

_LEVEL_PROP = 'battery.charge_level.percentage'

class Device(device.Device):
    __gproperties__ = {
        'level' : (int, None, None, 0, 100, 0,
                   gobject.PARAM_READABLE)
    }

    def __init__(self, udi):
        device.Device.__init__(self, udi)
        
        bus = dbus.Bus(dbus.Bus.TYPE_SYSTEM)
        proxy = bus.get_object('org.freedesktop.Hal', udi)
        self._battery = dbus.Interface(proxy, 'org.freedesktop.Hal.Device')
        bus.add_signal_receiver(self._battery_changed,
                                'PropertyModified',
                                'org.freedesktop.Hal.Device',
                                'org.freedesktop.Hal',
                                udi)

        self._level = self._battery.GetProperty(_LEVEL_PROP)

    def do_get_property(self, pspec):
        if pspec.name == 'level':
            return self._level 

    def get_type(self):
        return 'battery'

    def _battery_changed(self, num_changes, changes_list):
        for change in changes_list:
            if change[0] == 'battery.charge_level.percentage':
                self._level = self._battery.GetProperty(_LEVEL_PROP)
                self.notify('level')
