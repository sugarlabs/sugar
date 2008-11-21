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
import os

import dbus
import ConfigParser

from sugar import dispatch
from sugar import env

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

NM_802_11_AP_FLAGS_NONE = 0x00000000
NM_802_11_AP_FLAGS_PRIVACY = 0x00000001

NM_802_11_AP_SEC_NONE = 0x00000000
NM_802_11_AP_SEC_PAIR_WEP40 = 0x00000001
NM_802_11_AP_SEC_PAIR_WEP104 = 0x00000002
NM_802_11_AP_SEC_PAIR_TKIP = 0x00000004
NM_802_11_AP_SEC_PAIR_CCMP = 0x00000008
NM_802_11_AP_SEC_GROUP_WEP40 = 0x00000010
NM_802_11_AP_SEC_GROUP_WEP104 = 0x00000020
NM_802_11_AP_SEC_GROUP_TKIP = 0x00000040
NM_802_11_AP_SEC_GROUP_CCMP = 0x00000080
NM_802_11_AP_SEC_KEY_MGMT_PSK = 0x00000100
NM_802_11_AP_SEC_KEY_MGMT_802_1X = 0x00000200

NM_802_11_MODE_UNKNOWN = 0
NM_802_11_MODE_ADHOC = 1
NM_802_11_MODE_INFRA = 2

NM_802_11_DEVICE_CAP_NONE = 0x00000000
NM_802_11_DEVICE_CAP_CIPHER_WEP40 = 0x00000001
NM_802_11_DEVICE_CAP_CIPHER_WEP104 = 0x00000002
NM_802_11_DEVICE_CAP_CIPHER_TKIP = 0x00000004
NM_802_11_DEVICE_CAP_CIPHER_CCMP = 0x00000008
NM_802_11_DEVICE_CAP_WPA = 0x00000010
NM_802_11_DEVICE_CAP_RSN = 0x00000020

SETTINGS_SERVICE = 'org.freedesktop.NetworkManagerUserSettings'

NM_SETTINGS_PATH = '/org/freedesktop/NetworkManagerSettings'
NM_SETTINGS_IFACE = 'org.freedesktop.NetworkManagerSettings'
NM_CONNECTION_IFACE = 'org.freedesktop.NetworkManagerSettings.Connection'
NM_SECRETS_IFACE = 'org.freedesktop.NetworkManagerSettings.Connection.Secrets'

_nm_settings = None
_conn_counter = 0

class WirelessSecurity(object):
    def __init__(self):
        self.key_mgmt = None
        self.proto = None
        self.group = None
        self.pairwise = None

    def get_dict(self):
        wireless_security = {}

        if self.key_mgmt is not None:
            wireless_security['key-mgmt'] = self.key_mgmt
        if self.proto is not None:
            wireless_security['proto'] = self.proto
        if self.pairwise is not None:
            wireless_security['pairwise'] = self.pairwise
        if self.group is not None:
            wireless_security['group'] = self.group

        return wireless_security

class Wireless(object):
    def __init__(self):
        self.ssid = None

    def get_dict(self):
        return {'ssid': self.ssid}

class Connection(object):
    def __init__(self):
        self.id = None
        self.uuid = None
        self.type = None

    def get_dict(self):
        return {'id': self.id,
                'uuid': self.uuid,
                'type': self.type}

class Settings(object):
    def __init__(self):
        self.connection = Connection()
        self.wireless = Wireless()
        self.wireless_security = None

    def get_dict(self):
        settings = {}
        settings['connection'] = self.connection.get_dict()
        settings['802-11-wireless'] = self.wireless.get_dict()
        if self.wireless_security is not None:
            settings['802-11-wireless-security'] = \
                self.wireless_security.get_dict()
        return settings

class Secrets(object):
    def __init__(self):
        self.wep_key = None
        self.psk = None
        self.auth_alg = None

    def get_dict(self):
        secrets = {}

        if self.wep_key is not None:
            secrets['wep-key0'] = self.wep_key
        if self.psk is not None:
            secrets['psk'] = self.psk
        if self.auth_alg is not None:
            secrets['auth-alg'] = self.auth_alg

        return {'802-11-wireless-security': secrets}

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
        self._reply_cb(secrets.get_dict())

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
        self.save()

    def save(self):
        profile_path = env.get_profile_path()
        config_path = os.path.join(profile_path, 'nm', 'connections.cfg')

        config = ConfigParser.ConfigParser()
        try:
            try:
                if not config.read(config_path):
                    logging.error('Error reading the nm config file')
                    return
            except ConfigParser.ParsingError, e:
                logging.error('Error reading the nm config file: %s' % e)
                return
            identifier = self._settings.connection.id

            if identifier not in config.sections():
                config.add_section(identifier)
            config.set(identifier, 'type', self._settings.connection.type)
            config.set(identifier, 'ssid', self._settings.wireless.ssid)
            config.set(identifier, 'uuid', self._settings.connection.uuid)

            if self._settings.wireless_security is not None:
                if self._settings.wireless_security.key_mgmt is not None:
                    config.set(identifier, 'key-mgmt',
                               self._settings.wireless_security.key_mgmt)
                if self._settings.wireless_security.proto is not None:
                    config.set(identifier, 'proto',
                               self._settings.wireless_security.proto)
                if self._settings.wireless_security.pairwise is not None:
                    config.set(identifier, 'pairwise',
                               self._settings.wireless_security.pairwise)
                if self._settings.wireless_security.group is not None:
                    config.set(identifier, 'group',
                               self._settings.wireless_security.group)
            if self._secrets is not None:
                if self._settings.wireless_security.key_mgmt == 'none':
                    config.set(identifier, 'key', self._secrets.wep_key)
                    config.set(identifier, 'auth-alg', self._secrets.auth_alg)
                elif self._settings.wireless_security.key_mgmt == 'wpa-psk':
                    config.set(identifier, 'key', self._secrets.psk)
        except ConfigParser.Error, e:
            logging.error('Error constructing %s: %s' % (identifier, e))
        else:
            f = open(config_path, 'w')
            try:
                config.write(f)
            except ConfigParser.Error, e:
                logging.error('Can not write %s error: %s' % (config_path, e))
            f.close()

    @dbus.service.method(dbus_interface=NM_CONNECTION_IFACE,
                         in_signature='', out_signature='a{sa{sv}}')
    def GetSettings(self):
        return self._settings.get_dict()

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
            reply(self._secrets.get_dict())

def get_settings():
    global _nm_settings
    if _nm_settings is None:
        try:
            _nm_settings = NMSettings()
        except dbus.DBusException, e:
            logging.error('Cannot create the UserSettings service %s.', e)
        load_connections()
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
    profile_path = env.get_profile_path()
    config_path = os.path.join(profile_path, 'nm', 'connections.cfg')

    config = ConfigParser.ConfigParser()

    if not os.path.exists(config_path):
        if not os.path.exists(os.path.dirname(config_path)):
            os.makedirs(os.path.dirname(config_path), 0755)
        f = open(config_path, 'w')
        config.write(f)
        f.close()

    try:
        if not config.read(config_path):
            logging.error('Error reading the nm config file')
            return
    except ConfigParser.ParsingError, e:
        logging.error('Error reading the nm config file: %s' % e)
        return

    for section in config.sections():
        try:
            settings = Settings()
            settings.connection.id = section
            ssid = config.get(section, 'ssid')
            settings.wireless.ssid = dbus.ByteArray(ssid)
            uuid = config.get(section, 'uuid')
            settings.connection.uuid = uuid
            nmtype = config.get(section, 'type')
            settings.connection.type = nmtype

            secrets = None
            if config.has_option(section, 'key-mgmt'):
                secrets = Secrets()
                settings.wireless_security = WirelessSecurity()
                mgmt = config.get(section, 'key-mgmt')
                settings.wireless_security.key_mgmt = mgmt
                key = config.get(section, 'key')
                if mgmt == 'none':
                    secrets.wep_key = key
                    auth_alg = config.get(section, 'auth-alg')
                    secrets.auth_alg = auth_alg
                elif mgmt == 'wpa-psk':
                    secrets.psk = key
                    if config.has_option(section, 'proto'):
                        value = config.get(section, 'proto')
                        settings.wireless_security.proto = value
                    if config.has_option(section, 'group'):
                        value = config.get(section, 'group')
                        settings.wireless_security.group = value
                    if config.has_option(section, 'pairwise'):
                        value = config.get(section, 'pairwise')
                        settings.wireless_security.pairwise = value
        except ConfigParser.Error, e:
            logging.error('Error reading section: %s' % e)
        else:
            add_connection(ssid, settings, secrets)
