# Copyright (C) 2008 Red Hat, Inc.
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

import dbus

from sugar import dispatch

DEVICE_TYPE_802_11_WIRELESS = 2

DEVICE_STATE_UNKNOWN = 0
DEVICE_STATE_UNMANAGED = 1
DEVICE_STATE_UNAVAILABLE = 2
DEVICE_STATE_DISCONNECTED = 3
DEVICE_STATE_PREPARE = 4
DEVICE_STATE_CONFIG = 5
DEVICE_STATE_NEED_AUTH = 6
DEVICE_STATE_IP_CONFIG = 7
DEVICE_STATE_ACTIVATED = 8
DEVICE_STATE_FAILED = 9

AP_FLAGS_802_11_NONE = 0
AP_FLAGS_802_11_PRIVACY = 1

SETTINGS_SERVICE = 'org.freedesktop.NetworkManagerUserSettings'

NM_SETTINGS_PATH = '/org/freedesktop/NetworkManagerSettings'
NM_SETTINGS_IFACE = 'org.freedesktop.NetworkManagerSettings'
NM_CONNECTION_IFACE = 'org.freedesktop.NetworkManagerSettings.Connection'
NM_SECRETS_IFACE = 'org.freedesktop.NetworkManagerSettings.Connection.Secrets'

_nm_settings = None
_conn_counter = 0

class NMSettings(dbus.service.Object):
    def __init__(self):
        bus = dbus.SystemBus()
        bus_name = dbus.service.BusName(SETTINGS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, NM_SETTINGS_PATH)

        self.connections = {}
        self.secrets_request = dispatch.Signal()

    @dbus.service.method(dbus_interface=NM_SETTINGS_IFACE,
                         in_signature='', out_signature='ao')
    def ListConnections(self):
        return self.connections.values()

    @dbus.service.signal(NM_SETTINGS_IFACE, signature='o')
    def NewConnection(self, connection_path):
        pass

    def add_connection(self, ssid, conn):
        self.connections[ssid] = conn
        conn.secrets_request.connect(self.__secrets_request_cb)
        self.NewConnection(conn.path)

    def __secrets_request_cb(self, sender, **kwargs):
        self.secrets_request.send(self, connection=sender,
                                  response=kwargs['response'])

class SecretsResponse(object):
    ''' Intermediate object to report the secrets from the dialog
    back to the connection object and which will inform NM
    '''
    def __init__(self, connection, reply_cb, error_cb):
        self._connection = connection
        self._reply_cb = reply_cb
        self._error_cb = error_cb

    def set_secrets(self, secrets):
        self._connection.set_secrets(secrets)
        self._reply_cb(secrets)

    def set_error(self, error):
        self._error_cb(error)

class NMSettingsConnection(dbus.service.Object):
    def __init__(self, path, settings, secrets):
        bus = dbus.SystemBus()
        bus_name = dbus.service.BusName(SETTINGS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, path)

        self.path = path
        self.secrets_request = dispatch.Signal()

        self._settings = settings
        self._secrets = secrets

    def set_secrets(self, secrets):
        self._secrets = secrets

    @dbus.service.method(dbus_interface=NM_CONNECTION_IFACE,
                         in_signature='', out_signature='a{sa{sv}}')
    def GetSettings(self):
        return self._settings

    @dbus.service.method(dbus_interface=NM_SECRETS_IFACE,
                         async_callbacks=('reply', 'error'),
                         in_signature='sasb', out_signature='a{sa{sv}}')
    def GetSecrets(self, setting_name, hints, request_new, reply, error):
        logging.debug('Secrets requested for connection %s request_new=%s'
                      % (self.path, request_new))

        if request_new or self._secrets is None:
            # request_new is for example the case when the pw on the AP changes
            response = SecretsResponse(self, reply, error)
            try:
                self.secrets_request.send(self, response=response)
            except Exception, e:
                logging.error('Error requesting the secrets via dialog: %s' % e)
        else:
            reply(self._secrets)

def get_settings():
    global _nm_settings
    if _nm_settings is None:
        try:
            _nm_settings = NMSettings()
        except dbus.DBusException, e:
            logging.error('Cannot create the UserSettings service %s.', e)
    return _nm_settings

def find_connection(ssid):
    connections = get_settings().connections
    if ssid in connections:
        return connections[ssid]
    else:
        return None

def add_connection(ssid, settings, secrets=None):
    global _conn_counter

    path = NM_SETTINGS_PATH + '/' + str(_conn_counter)
    _conn_counter += 1

    conn = NMSettingsConnection(path, settings, secrets)
    _nm_settings.add_connection(ssid, conn)

    return conn

def load_connections():
    pass
