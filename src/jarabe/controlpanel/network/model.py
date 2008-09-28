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

import dbus
from gettext import gettext as _

from sugar import profile
from jarabe.hardware import hardwaremanager

NM_SERVICE_NAME = 'org.freedesktop.NetworkManager'
NM_SERVICE_PATH = '/org/freedesktop/NetworkManager'
NM_SERVICE_IFACE = 'org.freedesktop.NetworkManager'
NM_ASLEEP = 1

KEYWORDS = ['network', 'jabber', 'radio', 'server']

class ReadError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

def get_jabber():
    pro = profile.get_profile()    
    return pro.jabber_server

def print_jabber():
    print get_jabber()

def set_jabber(server):
    """Set the jabber server
    server : e.g. 'olpc.collabora.co.uk'
    """
    pro = profile.get_profile()
    pro.jabber_server = server
    pro.jabber_registered = False
    pro.save()
    return 1

def get_radio():    
    bus = dbus.SystemBus()
    proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
    nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
    state = nm.getWirelessEnabled()	
    if state in (0, 1):
        return state
    else:
        raise ReadError(_('State is unknown.'))
	
def print_radio():
    print ('off', 'on')[get_radio()]
    
def set_radio(state):
    """Turn Radio 'on' or 'off'
    state : 'on/off'
    """    
    if state == 'on' or state == 1:
        bus = dbus.SystemBus()
        proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
        nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
        nm.setWirelessEnabled(True)        
    elif state == 'off' or state == 0:
        bus = dbus.SystemBus()
        proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
        nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
        nm.setWirelessEnabled(False)
    else:
        raise ValueError(_("Error in specified radio argument use on/off."))

    return 0

def clear_registration():
    """Clear the registration with the schoolserver
    """
    pro = profile.get_profile()
    pro.backup1 = None
    pro.save()
    return 1

def clear_networks():
    """Clear saved passwords and network configurations.
    """
    network_manager = hardwaremanager.get_network_manager()
    if not network_manager:
        return
    network_manager.nminfo.delete_all_networks()
    return 1
