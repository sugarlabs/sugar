# Copyright (C) 2008 One Laptop Per Child
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
#

from gettext import gettext as _

from sugar import profile
import dbus

OHM_SERVICE_NAME = 'org.freedesktop.ohm'
OHM_SERVICE_PATH = '/org/freedesktop/ohm/Keystore'
OHM_SERVICE_IFACE = 'org.freedesktop.ohm.Keystore'

class ReadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def get_automatic_pm():
    pro = profile.get_profile()
    ret = pro.automatic_pm
    return ret

def print_automatic_pm():
    print ('off', 'on')[get_automatic_pm()]

def set_automatic_pm(enabled):
    """Automatic suspends on/off."""

    bus = dbus.SystemBus()
    proxy = bus.get_object(OHM_SERVICE_NAME, OHM_SERVICE_PATH)
    keystore = dbus.Interface(proxy, OHM_SERVICE_IFACE)
    
    if enabled == 'on' or enabled == 1:
        keystore.SetKey("suspend.automatic_pm", 1)
        enabled = True
    elif enabled == 'off' or enabled == 0:
        keystore.SetKey("suspend.automatic_pm", 0)
        enabled = False
    else:
        raise ValueError(_("Error in automatic pm argument, use on/off."))

    pro = profile.get_profile()
    pro.automatic_pm = enabled
    pro.save()
    return 0

def get_extreme_pm():
    pro = profile.get_profile()
    ret = pro.extreme_pm
    return ret

def print_extreme_pm():
    print ('off', 'on')[get_extreme_pm()]

def set_extreme_pm(enabled):
    """Extreme power management on/off."""
    
    bus = dbus.SystemBus()
    proxy = bus.get_object(OHM_SERVICE_NAME, OHM_SERVICE_PATH)
    keystore = dbus.Interface(proxy, OHM_SERVICE_IFACE)
    
    if enabled == 'on' or enabled == 1:
        keystore.SetKey("suspend.extreme_pm", 1)
        enabled = True
    elif enabled == 'off' or enabled == 0:
        keystore.SetKey("suspend.extreme_pm", 0)
        enabled = False
    else:
        raise ValueError(_("Error in extreme pm argument, use on/off."))

    pro = profile.get_profile()
    pro.extreme_pm = enabled
    pro.save()
    return 0
