# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2014 Sugar Labs, Frederick Grose
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

import logging

import dbus
from gettext import gettext as _
from gi.repository import Gio

from jarabe.model import network


_NM_SERVICE = 'org.freedesktop.NetworkManager'
_NM_PATH = '/org/freedesktop/NetworkManager'
_NM_IFACE = 'org.freedesktop.NetworkManager'

KEYWORDS = ['network', 'jabber', 'radio', 'server']


class ReadError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def get_jabber():
    settings = Gio.Settings('org.sugarlabs.collaboration')
    return settings.get_string('jabber-server')


def print_jabber():
    print get_jabber()


def set_jabber(server):
    """Set the jabber server
    server : e.g. 'olpc.collabora.co.uk'
    """
    settings = Gio.Settings('org.sugarlabs.collaboration')
    settings.set_string('jabber-server', server)

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/collaboration/jabber_server', server)

    return 0


def get_radio():
    try:
        bus = dbus.SystemBus()
        obj = bus.get_object(_NM_SERVICE, _NM_PATH)
        nm_props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
    except dbus.DBusException:
        raise ReadError('%s service not available' % _NM_SERVICE)

    state = nm_props.Get(_NM_IFACE, 'WirelessEnabled')
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
        try:
            bus = dbus.SystemBus()
            obj = bus.get_object(_NM_SERVICE, _NM_PATH)
            nm_props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
        except dbus.DBusException:
            raise ReadError('%s service not available' % _NM_SERVICE)
        nm_props.Set(_NM_IFACE, 'WirelessEnabled', True)
    elif state == 'off' or state == 0:
        try:
            bus = dbus.SystemBus()
            obj = bus.get_object(_NM_SERVICE, _NM_PATH)
            nm_props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
        except dbus.DBusException:
            raise ReadError('%s service not available' % _NM_SERVICE)
        nm_props.Set(_NM_IFACE, 'WirelessEnabled', False)
    else:
        raise ValueError(_('Error in specified radio argument use on/off.'))

    return 0


def clear_registration():
    """Clear the registration with the schoolserver
    """
    settings = Gio.Settings('org.sugarlabs')
    settings.set_string('backup-url', '')

    # DEPRECATED
    from gi.repository import GConf
    client = GConf.Client.get_default()
    client.set_string('/desktop/sugar/backup_url', '')
    return 1


def non_sugar_wireless(connection):
    """Check for wireless connection not internal to Sugar.
    """
    wifi_settings = connection.get_settings(
                               network.NM_CONNECTION_TYPE_802_11_WIRELESS)
    if wifi_settings:
        return not (wifi_settings['mode'] == 'adhoc' and
                    connection.get_id().startswith(
                                        network.ADHOC_CONNECTION_ID_PREFIX))

    mesh_settings = connection.get_settings(
                               network.NM_CONNECTION_TYPE_802_11_OLPC_MESH)
    if mesh_settings:
        return not (connection.get_id().startswith(
                                        network.MESH_CONNECTION_ID_PREFIX) or
                    connection.get_id().startswith(
                                        network.XS_MESH_CONNECTION_ID_PREFIX))


def clear_wireless_networks():
    """Remove all wireless connections except Sugar-internal ones.
    """
    try:
        connections = network.get_connections()
    except dbus.DBusException:
        logging.debug('NetworkManager not available')
    else:
        non_sugar_wireless_connections = (connection
                for connection in connections.get_list()
                    if non_sugar_wireless(connection))

        connections.clear(non_sugar_wireless_connections)


def have_wireless_networks():
    """Check that there are non-Sugar-internal wireless connections.
    """
    try:
        connections = network.get_connections()
        return any(non_sugar_wireless(connection)
                   for connection in connections.get_list())
    except dbus.DBusException:
        logging.debug('NetworkManager not available')
        return False


def get_publish_information():
    settings = Gio.Settings('org.sugarlabs.collaboration')
    publish = settings.get_boolean('publish-gadget')
    return publish


def print_publish_information():
    print get_publish_information()


def set_publish_information(value):
    """ If set to true, Sugar will make you searchable for
    the other users of the Jabber server.
    value: 0/1
    """
    try:
        value = (False, True)[int(value)]
    except:
        raise ValueError(_('Error in specified argument use 0/1.'))

    settings = Gio.Settings('org.sugarlabs.collaboration')
    settings.set_boolean('publish-gadget', value)
    return 0
