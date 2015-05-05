# Copyright (C) 2014 Sam Parkinson
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

import os

import dbus
from sugar3 import dispatch


_DISPLAYS_DIRECTORY = '/sys/class/backlight/'

_CONTROL_RAW = 0
_CONTROL_GNOME = 1

_POWER_NAME = 'org.gnome.SettingsDaemon.Power'
_POWER_PATH = '/org/gnome/SettingsDaemon/Power'
_SCREEN_IFACE = 'org.gnome.SettingsDaemon.Power.Screen'

class Brightness(object):

    brightness_changed = dispatch.Signal()

    def __init__(self):
        self._control = _CONTROL_RAW
        self._bus = dbus.SessionBus()

        display = os.listdir(_DISPLAYS_DIRECTORY)[0]
        brightness_directory = os.path.join(_DISPLAYS_DIRECTORY, display)
        self._brightness_path = os.path.join(brightness_directory,
                                             'brightness')
        self._can_set_brightness = os.access(self._brightness_path, os.W_OK)

        # GNOME provides a way to change root-writeable brightness values
        # Use it if avaliable
        if (not self._can_set_brightness) and \
            self._bus.name_has_owner(_POWER_NAME):
            self._control = _CONTROL_GNOME
            self._can_set_brightness = True
            self._max_brightness = 100  # Percentages are used

            power = self._bus.get_object(_POWER_NAME, _POWER_PATH)
            self._dbus_props = dbus.Interface(power, dbus.PROPERTIES_IFACE)
        else:
            with open(os.path.join(brightness_directory,
                      'max_brightness')) as f:
                self._max_brightness = int(f.read())

    def get_brightness(self):
        if self._control == _CONTROL_RAW:
            with open(self._brightness_path) as f:
                return int(f.read())
        else:
            return int(self._dbus_props.Get(_SCREEN_IFACE, 'Brightness'))

    def set_brightness(self, brightness):
        '''
        Sets the brightness with an int ranging from 0 to max_brightness.
        '''
        if not self._can_set_brightness:
            return

        if brightness < 0 or brightness > self._max_brightness:
            return

        if self._control == _CONTROL_RAW:
            with open(self._brightness_path, 'w') as f:
                f.write(str(brightness))
        else:
            self._dbus_props.Set(_SCREEN_IFACE, 'Brightness', brightness)

        self.brightness_changed.send(None)

    def can_set_brightness(self):
        return self._can_set_brightness

    def get_max_brightness(self):
        return self._max_brightness


brightness = Brightness()
