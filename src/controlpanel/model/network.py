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
    if not server:
        raise ValueError(_("You must enter a server."))
    pro = profile.get_profile()
    pro.jabber_server = server
    pro.jabber_registered = False
    pro.save()
    return "RESTART"

def get_radio():    
    bus = dbus.SystemBus()
    proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
    nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
    state = nm.getWirelessEnabled()	
    if state == 0:
        return _('off')
    elif state == 1:
        return _('on')
    else:
        raise ReadError(_('State is unknown.'))
	
def print_radio():
    print get_radio()
    
def set_radio(state):
    """Turn Radio 'on' or 'off'
    state : 'on/off'
    """    
    if state == 'on':
        bus = dbus.SystemBus()
        proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
        nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
        nm.setWirelessEnabled(True)        
    elif state == 'off':
        bus = dbus.SystemBus()
        proxy = bus.get_object(NM_SERVICE_NAME, NM_SERVICE_PATH)
        nm = dbus.Interface(proxy, NM_SERVICE_IFACE)
        nm.setWirelessEnabled(False)
    else:
        raise ValueError(_("Error in specified radio argument use on/off."))

