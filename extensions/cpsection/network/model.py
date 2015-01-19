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
from gi.repository import NMClient

from jarabe.model import network


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
        nm_client = NMClient.Client()
        return nm_client.wireless_get_enabled()
    except:
        raise ReadError(_('State is unknown.'))


def print_radio():
    print ('off', 'on')[get_radio()]


def set_radio(state):
    """Turn Radio 'on' or 'off'
    state : 'on/off'
    """
    try:
        state = state or state == 'on' or state == 1
        nm_client = NMClient.Client()
        nm_client.wireless_set_enabled(state)
    except:
        raise ValueError(_('Error in specified radio argument use on/off.'))


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


wifi_whitelist = ('Sugar Ad-hoc Network 1',
                  'Sugar Ad-hoc Network 6',
                  'Sugar Ad-hoc Network 11')
mesh_whitelist = ('OLPC Mesh Network 1',
                  'OLPC Mesh Network 6',
                  'OLPC Mesh Network 11',
                  'OLPC XS Mesh Network 1',
                  'OLPC XS Mesh Network 6',
                  'OLPC XS Mesh Network 11')


def is_wireless(connection):
    """Check for wireless connection not whitelisted by Sugar.
    """
    wifi_settings = connection.get_settings(
        network.NM_CONNECTION_TYPE_802_11_WIRELESS)
    if wifi_settings:
        return not (wifi_settings['mode'] == 'adhoc' and
                    connection.get_id() in wifi_whitelist)

    mesh_settings = connection.get_settings(
        network.NM_CONNECTION_TYPE_802_11_OLPC_MESH)
    if mesh_settings:
        return not connection.get_id() in mesh_whitelist


def clear_wireless_networks():
    """Remove all wireless connections except Sugar-internal ones.
    """
    try:
        connections = network.get_connections()
    except dbus.DBusException:
        logging.debug('NetworkManager not available')
    else:
        wireless_connections = \
            (connection for connection in
             connections.get_list() if is_wireless(connection))

        for connection in wireless_connections:
            try:
                connection.delete()
            except dbus.DBusException:
                logging.debug("Could not remove connection %s",
                              connection.get_id())


def have_wireless_networks():
    """Check that there are non-Sugar-internal wireless connections.
    """
    try:
        connections = network.get_connections()
    except dbus.DBusException:
        logging.debug('NetworkManager not available')
        return False
    else:
        return any(is_wireless(connection)
                   for connection in connections.get_list())


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
