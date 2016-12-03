# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2014 Sugar Labs, Frederick Grose
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
#

import logging

import gi
gi.require_version('NMClient', '1.0')
from gettext import gettext as _
from gi.repository import Gio
from gi.repository import NMClient

from jarabe.model import network


KEYWORDS = ['network', 'jabber', 'radio', 'server', 'social', 'help']


class ReadError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


def get_social_help():
    settings = Gio.Settings('org.sugarlabs.collaboration')
    return settings.get_string('social-help-server')


def set_social_help(server):
    """
    Set the social-help server

    e.g. 'https://use-socialhelp.sugarlabs.org'
    """
    settings = Gio.Settings('org.sugarlabs.collaboration')
    server = server.strip().rstrip('/')
    # Don't add http:// to a null input
    if server and '://' not in server:
        server = 'http://' + server
    settings.set_string('social-help-server', server)


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
        nm_client.wireless_set_enabled(state)
    except:
        raise ValueError(_('Error in specified radio argument. Use on/off.'))


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


def clear_wireless_networks():
    network.clear_wireless_networks()


def have_wireless_networks():
    return network.have_wireless_networks()


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
        raise ValueError(_('Error in specified argument. Use 0/1.'))

    settings = Gio.Settings('org.sugarlabs.collaboration')
    settings.set_boolean('publish-gadget', value)
    return 0

nm_client = NMClient.Client()
