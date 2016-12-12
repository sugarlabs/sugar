# Copyright (C) 2008 Red Hat, Inc.
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009-2010 One Laptop per Child
# Copyright (C) 2009 Paraguay Educa, Martin Abente
# Copyright (C) 2010 Plan Ceibal, Daniel Castelo
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

from gettext import gettext as _
import logging
import os
import uuid

import dbus
import dbus.service
from gi.repository import GObject
import ConfigParser
from gi.repository import Gio
import ctypes

from sugar3 import dispatch
from sugar3 import env

from jarabe.model.update.updater import check_urgent_update

NM_STATE_UNKNOWN = 0
NM_STATE_ASLEEP = 10
NM_STATE_DISCONNECTED = 20
NM_STATE_DISCONNECTING = 30
NM_STATE_CONNECTING = 40
NM_STATE_CONNECTED_LOCAL = 50
NM_STATE_CONNECTED_SITE = 60
NM_STATE_CONNECTED_GLOBAL = 70

NM_DEVICE_TYPE_UNKNOWN = 0
NM_DEVICE_TYPE_ETHERNET = 1
NM_DEVICE_TYPE_WIFI = 2
NM_DEVICE_TYPE_UNUSED1 = 3
NM_DEVICE_TYPE_UNUSED2 = 4
NM_DEVICE_TYPE_BT = 5
NM_DEVICE_TYPE_OLPC_MESH = 6
NM_DEVICE_TYPE_WIMAX = 7
NM_DEVICE_TYPE_MODEM = 8

NM_DEVICE_STATE_UNKNOWN = 0
NM_DEVICE_STATE_UNMANAGED = 10
NM_DEVICE_STATE_UNAVAILABLE = 20
NM_DEVICE_STATE_DISCONNECTED = 30
NM_DEVICE_STATE_PREPARE = 40
NM_DEVICE_STATE_CONFIG = 50
NM_DEVICE_STATE_NEED_AUTH = 60
NM_DEVICE_STATE_IP_CONFIG = 70
NM_DEVICE_STATE_IP_CHECK = 80
NM_DEVICE_STATE_SECONDARIES = 90
NM_DEVICE_STATE_ACTIVATED = 100
NM_DEVICE_STATE_DEACTIVATING = 110
NM_DEVICE_STATE_FAILED = 120

NM_CONNECTION_TYPE_802_11_OLPC_MESH = '802-11-olpc-mesh'
NM_CONNECTION_TYPE_802_11_WIRELESS = '802-11-wireless'
NM_CONNECTION_TYPE_GSM = 'gsm'

NM_ACTIVE_CONNECTION_STATE_UNKNOWN = 0
NM_ACTIVE_CONNECTION_STATE_ACTIVATING = 1
NM_ACTIVE_CONNECTION_STATE_ACTIVATED = 2
NM_ACTIVE_CONNECTION_STATE_DEACTIVATING = 3

NM_DEVICE_STATE_REASON_UNKNOWN = 0
NM_DEVICE_STATE_REASON_NONE = 1
NM_DEVICE_STATE_REASON_NOW_MANAGED = 2
NM_DEVICE_STATE_REASON_NOW_UNMANAGED = 3
NM_DEVICE_STATE_REASON_CONFIG_FAILED = 4
NM_DEVICE_STATE_REASON_IP_CONFIG_UNAVAILABLE = 5
NM_DEVICE_STATE_REASON_IP_CONFIG_EXPIRED = 6
NM_DEVICE_STATE_REASON_NO_SECRETS = 7
NM_DEVICE_STATE_REASON_SUPPLICANT_DISCONNECT = 8
NM_DEVICE_STATE_REASON_SUPPLICANT_CONFIG_FAILED = 9
NM_DEVICE_STATE_REASON_SUPPLICANT_FAILED = 10
NM_DEVICE_STATE_REASON_SUPPLICANT_TIMEOUT = 11
NM_DEVICE_STATE_REASON_PPP_START_FAILED = 12
NM_DEVICE_STATE_REASON_PPP_DISCONNECT = 13
NM_DEVICE_STATE_REASON_PPP_FAILED = 14
NM_DEVICE_STATE_REASON_DHCP_START_FAILED = 15
NM_DEVICE_STATE_REASON_DHCP_ERROR = 16
NM_DEVICE_STATE_REASON_DHCP_FAILED = 17
NM_DEVICE_STATE_REASON_SHARED_START_FAILED = 18
NM_DEVICE_STATE_REASON_SHARED_FAILED = 19
NM_DEVICE_STATE_REASON_AUTOIP_START_FAILED = 20
NM_DEVICE_STATE_REASON_AUTOIP_ERROR = 21
NM_DEVICE_STATE_REASON_AUTOIP_FAILED = 22
NM_DEVICE_STATE_REASON_MODEM_BUSY = 23
NM_DEVICE_STATE_REASON_MODEM_NO_DIAL_TONE = 24
NM_DEVICE_STATE_REASON_MODEM_NO_CARRIER = 25
NM_DEVICE_STATE_REASON_MODEM_DIAL_TIMEOUT = 26
NM_DEVICE_STATE_REASON_MODEM_DIAL_FAILED = 27
NM_DEVICE_STATE_REASON_MODEM_INIT_FAILED = 28
NM_DEVICE_STATE_REASON_GSM_APN_FAILED = 29
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_NOT_SEARCHING = 30
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_DENIED = 31
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_TIMEOUT = 32
NM_DEVICE_STATE_REASON_GSM_REGISTRATION_FAILED = 33
NM_DEVICE_STATE_REASON_GSM_PIN_CHECK_FAILED = 34
NM_DEVICE_STATE_REASON_FIRMWARE_MISSING = 35
NM_DEVICE_STATE_REASON_REMOVED = 36
NM_DEVICE_STATE_REASON_SLEEPING = 37
NM_DEVICE_STATE_REASON_CONNECTION_REMOVED = 38
NM_DEVICE_STATE_REASON_USER_REQUESTED = 39
NM_DEVICE_STATE_REASON_CARRIER = 40
NM_DEVICE_STATE_REASON_CONNECTION_ASSUMED = 41
NM_DEVICE_STATE_REASON_SUPPLICANT_AVAILABLE = 42
NM_DEVICE_STATE_REASON_MODEM_NOT_FOUND = 43
NM_DEVICE_STATE_REASON_BT_FAILED = 44
NM_DEVICE_STATE_REASON_LAST = 0xFFFF

NM_802_11_AP_FLAGS_NONE = 0x00000000
NM_802_11_AP_FLAGS_PRIVACY = 0x00000001

NM_802_11_AP_SEC_NONE = 0x0
NM_802_11_AP_SEC_PAIR_WEP40 = 0x1
NM_802_11_AP_SEC_PAIR_WEP104 = 0x2
NM_802_11_AP_SEC_PAIR_TKIP = 0x4
NM_802_11_AP_SEC_PAIR_CCMP = 0x8
NM_802_11_AP_SEC_GROUP_WEP40 = 0x10
NM_802_11_AP_SEC_GROUP_WEP104 = 0x20
NM_802_11_AP_SEC_GROUP_TKIP = 0x40
NM_802_11_AP_SEC_GROUP_CCMP = 0x80
NM_802_11_AP_SEC_KEY_MGMT_PSK = 0x100
NM_802_11_AP_SEC_KEY_MGMT_802_1X = 0x200

NM_802_11_MODE_UNKNOWN = 0
NM_802_11_MODE_ADHOC = 1
NM_802_11_MODE_INFRA = 2

NM_WIFI_DEVICE_CAP_NONE = 0x00000000
NM_WIFI_DEVICE_CAP_CIPHER_WEP40 = 0x00000001
NM_WIFI_DEVICE_CAP_CIPHER_WEP104 = 0x00000002
NM_WIFI_DEVICE_CAP_CIPHER_TKIP = 0x00000004
NM_WIFI_DEVICE_CAP_CIPHER_CCMP = 0x00000008
NM_WIFI_DEVICE_CAP_WPA = 0x00000010
NM_WIFI_DEVICE_CAP_RSN = 0x00000020

NM_BT_CAPABILITY_NONE = 0x00000000
NM_BT_CAPABILITY_DUN = 0x00000001
NM_BT_CAPABILITY_NAP = 0x00000002

NM_DEVICE_MODEM_CAPABILITY_NONE = 0x00000000
NM_DEVICE_MODEM_CAPABILITY_POTS = 0x00000001
NM_DEVICE_MODEM_CAPABILITY_CDMA_EVDO = 0x00000002
NM_DEVICE_MODEM_CAPABILITY_GSM_UMTS = 0x00000004
NM_DEVICE_MODEM_CAPABILITY_LTE = 0x00000008

SETTINGS_SERVICE = 'org.freedesktop.NetworkManager'

NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_IFACE = 'org.freedesktop.NetworkManager'
NM_PATH = '/org/freedesktop/NetworkManager'
NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
NM_WIRED_IFACE = 'org.freedesktop.NetworkManager.Device.Wired'
NM_WIRELESS_IFACE = 'org.freedesktop.NetworkManager.Device.Wireless'
NM_MODEM_IFACE = 'org.freedesktop.NetworkManager.Device.Modem'
NM_OLPC_MESH_IFACE = 'org.freedesktop.NetworkManager.Device.OlpcMesh'
NM_SETTINGS_PATH = '/org/freedesktop/NetworkManager/Settings'
NM_SETTINGS_IFACE = 'org.freedesktop.NetworkManager.Settings'
NM_CONNECTION_IFACE = 'org.freedesktop.NetworkManager.Settings.Connection'
NM_ACCESSPOINT_IFACE = 'org.freedesktop.NetworkManager.AccessPoint'
NM_ACTIVE_CONN_IFACE = 'org.freedesktop.NetworkManager.Connection.Active'

NM_SECRET_AGENT_IFACE = 'org.freedesktop.NetworkManager.SecretAgent'
NM_SECRET_AGENT_PATH = '/org/freedesktop/NetworkManager/SecretAgent'
NM_AGENT_MANAGER_IFACE = 'org.freedesktop.NetworkManager.AgentManager'
NM_AGENT_MANAGER_PATH = '/org/freedesktop/NetworkManager/AgentManager'

NM_AGENT_MANAGER_ERR_NO_SECRETS = \
    'org.freedesktop.NetworkManager.AgentManager.NoSecrets'

GSM_CONNECTION_ID = 'Sugar Modem Connection'
GSM_BAUD_RATE = 115200
GSM_KEYS_PATH = 'org.sugarlabs.network.gsm'
GSM_USERNAME_KEY = 'username'
GSM_PASSWORD_KEY = 'password'
GSM_NUMBER_KEY = 'number'
GSM_APN_KEY = 'apn'
GSM_PIN_KEY = 'pin'
GSM_PUK_KEY = 'puk'

ADHOC_CONNECTION_ID_PREFIX = 'Sugar Ad-hoc Network '
MESH_CONNECTION_ID_PREFIX = 'OLPC Mesh Network '
XS_MESH_CONNECTION_ID_PREFIX = 'OLPC XS Mesh Network '

_network_manager = None
_nm_settings = None
_secret_agent = None
_connections = None
_interfaces = None

_nm_device_state_reason_description = None


def get_error_by_reason(reason):
    global _nm_device_state_reason_description

    if _nm_device_state_reason_description is None:
        _nm_device_state_reason_description = {
            NM_DEVICE_STATE_REASON_UNKNOWN:
            _('The reason for the device state change is unknown.'),
            NM_DEVICE_STATE_REASON_NONE:
            _('The state change is normal.'),
            NM_DEVICE_STATE_REASON_NOW_MANAGED:
            _('The device is now managed.'),
            NM_DEVICE_STATE_REASON_NOW_UNMANAGED:
            _('The device is no longer managed.'),
            NM_DEVICE_STATE_REASON_CONFIG_FAILED:
            _('The device could not be readied for configuration.'),
            NM_DEVICE_STATE_REASON_IP_CONFIG_UNAVAILABLE:
            _('IP configuration could not be reserved '
              '(no available address, timeout, etc).'),
            NM_DEVICE_STATE_REASON_IP_CONFIG_EXPIRED:
            _('The IP configuration is no longer valid.'),
            NM_DEVICE_STATE_REASON_NO_SECRETS:
            _('Secrets were required, but not provided.'),
            NM_DEVICE_STATE_REASON_SUPPLICANT_DISCONNECT:
            _('The 802.1X supplicant disconnected from '
              'the access point or authentication server.'),
            NM_DEVICE_STATE_REASON_SUPPLICANT_CONFIG_FAILED:
            _('Configuration of the 802.1X supplicant failed.'),
            NM_DEVICE_STATE_REASON_SUPPLICANT_FAILED:
            _('The 802.1X supplicant quit or failed unexpectedly.'),
            NM_DEVICE_STATE_REASON_SUPPLICANT_TIMEOUT:
            _('The 802.1X supplicant took too long to authenticate.'),
            NM_DEVICE_STATE_REASON_PPP_START_FAILED:
            _('The PPP service failed to start within the allowed time.'),
            NM_DEVICE_STATE_REASON_PPP_DISCONNECT:
            _('The PPP service disconnected unexpectedly.'),
            NM_DEVICE_STATE_REASON_PPP_FAILED:
            _('The PPP service quit or failed unexpectedly.'),
            NM_DEVICE_STATE_REASON_DHCP_START_FAILED:
            _('The DHCP service failed to start within the allowed time.'),
            NM_DEVICE_STATE_REASON_DHCP_ERROR:
            _('The DHCP service reported an unexpected error.'),
            NM_DEVICE_STATE_REASON_DHCP_FAILED:
            _('The DHCP service quit or failed unexpectedly.'),
            NM_DEVICE_STATE_REASON_SHARED_START_FAILED:
            _('The shared connection service failed to start.'),
            NM_DEVICE_STATE_REASON_SHARED_FAILED:
            _('The shared connection service quit or failed'
              ' unexpectedly.'),
            NM_DEVICE_STATE_REASON_AUTOIP_START_FAILED:
            _('The AutoIP service failed to start.'),
            NM_DEVICE_STATE_REASON_AUTOIP_ERROR:
            _('The AutoIP service reported an unexpected error.'),
            NM_DEVICE_STATE_REASON_AUTOIP_FAILED:
            _('The AutoIP service quit or failed unexpectedly.'),
            NM_DEVICE_STATE_REASON_MODEM_BUSY:
            _('Dialing failed because the line was busy.'),
            NM_DEVICE_STATE_REASON_MODEM_NO_DIAL_TONE:
            _('Dialing failed because there was no dial tone.'),
            NM_DEVICE_STATE_REASON_MODEM_NO_CARRIER:
            _('Dialing failed because there was no carrier.'),
            NM_DEVICE_STATE_REASON_MODEM_DIAL_TIMEOUT:
            _('Dialing timed out.'),
            NM_DEVICE_STATE_REASON_MODEM_DIAL_FAILED:
            _('Dialing failed.'),
            NM_DEVICE_STATE_REASON_MODEM_INIT_FAILED:
            _('Modem initialization failed.'),
            NM_DEVICE_STATE_REASON_GSM_APN_FAILED:
            _('Failed to select the specified GSM APN'),
            NM_DEVICE_STATE_REASON_GSM_REGISTRATION_NOT_SEARCHING:
            _('Not searching for networks.'),
            NM_DEVICE_STATE_REASON_GSM_REGISTRATION_DENIED:
            _('Network registration was denied.'),
            NM_DEVICE_STATE_REASON_GSM_REGISTRATION_TIMEOUT:
            _('Network registration timed out.'),
            NM_DEVICE_STATE_REASON_GSM_REGISTRATION_FAILED:
            _('Failed to register with the requested GSM network.'),
            NM_DEVICE_STATE_REASON_GSM_PIN_CHECK_FAILED:
            _('PIN check failed.'),
            NM_DEVICE_STATE_REASON_FIRMWARE_MISSING:
            _('Necessary firmware for the device may be missing.'),
            NM_DEVICE_STATE_REASON_REMOVED:
            _('The device was removed.'),
            NM_DEVICE_STATE_REASON_SLEEPING:
            _('NetworkManager went to sleep.'),
            NM_DEVICE_STATE_REASON_CONNECTION_REMOVED:
            _("The device's active connection was removed "
              "or disappeared."),
            NM_DEVICE_STATE_REASON_USER_REQUESTED:
            _('A user or client requested the disconnection.'),
            NM_DEVICE_STATE_REASON_CARRIER:
            _("The device's carrier/link changed."),
            NM_DEVICE_STATE_REASON_CONNECTION_ASSUMED:
            _("The device's existing connection was assumed."),
            NM_DEVICE_STATE_REASON_SUPPLICANT_AVAILABLE:
            _("The supplicant is now available."),
            NM_DEVICE_STATE_REASON_MODEM_NOT_FOUND:
            _("The modem could not be found."),
            NM_DEVICE_STATE_REASON_BT_FAILED:
            _("The Bluetooth connection failed or timed out."),
            NM_DEVICE_STATE_REASON_LAST:
            _("Unused."),
        }

    return _nm_device_state_reason_description[reason]


def frequency_to_channel(frequency):
    """Returns the channel matching a given radio channel frequency. If a
    frequency is not in the dictionary channel 0 will be returned.

    Keyword arguments:
    frequency -- The radio channel frequency in MHz.

    Return: Channel represented by the frequency or 0

    """

    bg_table = {2412: 1, 2417: 2, 2422: 3, 2427: 4,
                2432: 5, 2437: 6, 2442: 7, 2447: 8,
                2452: 9, 2457: 10, 2462: 11, 2467: 12,
                2472: 13, 14: 2484}

    a_table = {5035: 7, 5040: 8, 5045: 9, 5055: 11,
               5060: 12, 5080: 16, 5170: 34,
               5180: 36, 5190: 38, 5200: 40,
               5210: 42, 5220: 44, 5230: 46,
               5240: 48, 5250: 50, 5260: 52,
               5280: 56, 5290: 58, 5300: 60,
               5320: 64, 5500: 100, 5520: 104,
               5540: 108, 5560: 112, 5580: 116,
               5600: 120, 5620: 124, 5640: 128,
               5660: 132, 5680: 136, 5700: 140,
               5745: 149, 5760: 152, 5765: 153,
               5785: 157, 5800: 160, 5805: 161,
               5825: 165, 4915: 183, 4920: 184,
               4925: 185, 4935: 187, 4945: 188,
               4960: 192, 4980: 196}
    if frequency not in bg_table and frequency not in a_table:
        logging.warning('The frequency %s can not be mapped to a channel, '
                        'returning 0.', frequency)
        return 0

    if frequency > 4900:
        return a_table[frequency]
    else:
        return bg_table[frequency]


def is_sugar_adhoc_network(ssid):
    """Checks whether an access point is a sugar Ad-hoc network.

    Keyword arguments:
    ssid -- Ssid of the access point.

    Return: Boolean

    """
    return ssid.startswith('Ad-hoc Network')


class WirelessSecurity(object):

    def __init__(self):
        self.key_mgmt = None
        self.proto = None
        self.group = None
        self.pairwise = None
        self.wep_key = None
        self.psk = None
        self.auth_alg = None

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
        if self.wep_key is not None:
            wireless_security['wep-key0'] = self.wep_key
        if self.psk is not None:
            wireless_security['psk'] = self.psk
        if self.auth_alg is not None:
            wireless_security['auth-alg'] = self.auth_alg
        return wireless_security


class Wireless(object):
    nm_name = '802-11-wireless'

    def __init__(self):
        self.ssid = None
        self.security = None
        self.mode = None
        self.band = None
        self.channel = None

    def get_dict(self):
        wireless = {'ssid': self.ssid}
        if self.security:
            wireless['security'] = self.security
        if self.mode:
            wireless['mode'] = self.mode
        if self.band:
            wireless['band'] = self.band
        if self.channel:
            wireless['channel'] = self.channel
        return wireless


class OlpcMesh(object):
    nm_name = '802-11-olpc-mesh'

    def __init__(self, channel, anycast_addr):
        self.channel = channel
        self.anycast_addr = anycast_addr

    def get_dict(self):
        ret = {
            'ssid': dbus.ByteArray('olpc-mesh'),
            'channel': self.channel,
        }

        if self.anycast_addr:
            ret['dhcp-anycast-address'] = dbus.ByteArray(self.anycast_addr)
        return ret


class ConnectionSettings(object):

    def __init__(self):
        self.id = None
        self.uuid = None
        self.type = None
        self.autoconnect = False
        self.timestamp = None

    def get_dict(self):
        connection = {'id': self.id,
                      'uuid': self.uuid,
                      'type': self.type,
                      'autoconnect': self.autoconnect}
        if self.timestamp:
            connection['timestamp'] = self.timestamp
        return connection


class IP4Config(object):

    def __init__(self):
        self.method = None

    def get_dict(self):
        ip4_config = {}
        if self.method is not None:
            ip4_config['method'] = self.method
        return ip4_config


class Serial(object):

    def __init__(self):
        self.baud = None

    def get_dict(self):
        serial = {}

        if self.baud is not None:
            serial['baud'] = self.baud

        return serial


class Ppp(object):

    def __init__(self):
        pass

    def get_dict(self):
        ppp = {}
        return ppp


class Gsm(object):

    def __init__(self):
        self.apn = None
        self.number = None
        self.username = None
        self.pin = None
        self.password = None

    def get_dict(self):
        gsm = {}

        if self.apn:
            gsm['apn'] = self.apn
        if self.number:
            gsm['number'] = self.number
        if self.username:
            gsm['username'] = self.username
        if self.password:
            gsm['password'] = self.password
        if self.pin:
            gsm['pin'] = self.pin

        return gsm


class Settings(object):

    def __init__(self, wireless_cfg=None):
        self.connection = ConnectionSettings()
        self.ip4_config = None
        self.wireless_security = None

        if wireless_cfg is not None:
            self.wireless = wireless_cfg
        else:
            self.wireless = Wireless()

    def get_dict(self):
        settings = {}
        settings['connection'] = self.connection.get_dict()
        settings[self.wireless.nm_name] = self.wireless.get_dict()
        if self.wireless_security is not None:
            settings['802-11-wireless-security'] = \
                self.wireless_security.get_dict()
        if self.ip4_config is not None:
            settings['ipv4'] = self.ip4_config.get_dict()
        return settings


class SettingsGsm(object):

    def __init__(self):
        self.connection = ConnectionSettings()
        self.ip4_config = IP4Config()
        self.serial = Serial()
        self.ppp = Ppp()
        self.gsm = Gsm()

    def get_dict(self):
        settings = {}

        settings['connection'] = self.connection.get_dict()
        settings['serial'] = self.serial.get_dict()
        settings['ppp'] = self.ppp.get_dict()
        settings['gsm'] = self.gsm.get_dict()
        settings['ipv4'] = self.ip4_config.get_dict()

        return settings


class SecretsResponse(object):
    """Intermediate object to report the secrets from the dialog
    back to the connection object and which will inform NM
    """

    def __init__(self, reply_cb, error_cb):
        self._reply_cb = reply_cb
        self._error_cb = error_cb

    def set_secrets(self, secrets):
        self._reply_cb(secrets)

    def set_error(self, error):
        self._error_cb(error)


def set_connected():
    try:
        # try to flush resolver cache - SL#1940
        # ctypes' syntactic sugar does not work
        # so we must get the func ptr explicitly
        libc = ctypes.CDLL('libc.so.6')
        res_init = getattr(libc, '__res_init')
        res_init(None)
    except:
        # pylint: disable=W0702
        logging.exception('Error calling libc.__res_init')

    check_urgent_update()


class SecretAgent(dbus.service.Object):

    def __init__(self):
        self._bus = dbus.SystemBus()
        dbus.service.Object.__init__(self, self._bus, NM_SECRET_AGENT_PATH)
        self.secrets_request = dispatch.Signal()
        proxy = self._bus.get_object(NM_IFACE, NM_AGENT_MANAGER_PATH)
        proxy.Register("org.sugarlabs.sugar",
                       dbus_interface=NM_AGENT_MANAGER_IFACE,
                       reply_handler=self._register_reply_cb,
                       error_handler=self._register_error_cb)

    def _register_reply_cb(self):
        logging.debug("SecretAgent registered")

    def _register_error_cb(self, error):
        logging.error("Failed to register SecretAgent: %s", error)

    @dbus.service.method(NM_SECRET_AGENT_IFACE,
                         async_callbacks=('reply', 'error'),
                         in_signature='a{sa{sv}}osasb',
                         out_signature='a{sa{sv}}',
                         sender_keyword='sender',
                         byte_arrays=True)
    def GetSecrets(self, settings, connection_path, setting_name, hints,
                   request_new, reply, error, sender=None):
        if setting_name != '802-11-wireless-security':
            raise ValueError("Unsupported setting type %s" % (setting_name,))
        if not sender:
            raise Exception("Internal error: couldn't get sender")
        uid = self._bus.get_unix_user(sender)
        if uid != 0:
            raise Exception("UID %d not authorized" % (uid,))

        response = SecretsResponse(reply, error)
        self.secrets_request.send(self, settings=settings, response=response)


class AccessPoint(GObject.GObject):
    __gsignals__ = {
        'props-changed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self, device, model):
        GObject.GObject.__init__(self)
        self.device = device
        self.model = model

        self._initialized = False
        self._bus = dbus.SystemBus()

        self.ssid = ''
        self.strength = 0
        self.flags = 0
        self.wpa_flags = 0
        self.rsn_flags = 0
        self.mode = 0
        self.channel = 0

    def initialize(self):
        model_props = dbus.Interface(self.model, dbus.PROPERTIES_IFACE)
        model_props.GetAll(NM_ACCESSPOINT_IFACE, byte_arrays=True,
                           reply_handler=self._ap_properties_changed_cb,
                           error_handler=self._get_all_props_error_cb)

        self._bus.add_signal_receiver(self._ap_properties_changed_cb,
                                      signal_name='PropertiesChanged',
                                      path=self.model.object_path,
                                      dbus_interface=NM_ACCESSPOINT_IFACE,
                                      byte_arrays=True)

    def network_hash(self):
        """
        This is a hash which uniquely identifies the network that this AP
        is a bridge to. i.e. its expected for 2 APs with identical SSID and
        other settings to have the same network hash, because we assume that
        they are a part of the same underlying network.
        """

        # based on logic from nm-applet
        fl = 0

        if self.mode == NM_802_11_MODE_INFRA:
            fl |= 1 << 0
        elif self.mode == NM_802_11_MODE_ADHOC:
            fl |= 1 << 1
        else:
            fl |= 1 << 2

        # Separate out no encryption, WEP-only, and WPA-capable */
        if (not (self.flags & NM_802_11_AP_FLAGS_PRIVACY)) \
                and self.wpa_flags == NM_802_11_AP_SEC_NONE \
                and self.rsn_flags == NM_802_11_AP_SEC_NONE:
            fl |= 1 << 3
        elif (self.flags & NM_802_11_AP_FLAGS_PRIVACY) \
                and self.wpa_flags == NM_802_11_AP_SEC_NONE \
                and self.rsn_flags == NM_802_11_AP_SEC_NONE:
            fl |= 1 << 4
        elif (not (self.flags & NM_802_11_AP_FLAGS_PRIVACY)) \
                and self.wpa_flags != NM_802_11_AP_SEC_NONE \
                and self.rsn_flags != NM_802_11_AP_SEC_NONE:
            fl |= 1 << 5
        else:
            fl |= 1 << 6

        hashstr = str(fl) + '@' + self.ssid
        return hash(hashstr)

    def _update_properties(self, properties):
        if self._initialized:
            old_hash = self.network_hash()
        else:
            old_hash = None

        if 'Ssid' in properties:
            self.ssid = properties['Ssid']
        if 'Strength' in properties:
            self.strength = properties['Strength']
        if 'Flags' in properties:
            self.flags = properties['Flags']
        if 'WpaFlags' in properties:
            self.wpa_flags = properties['WpaFlags']
        if 'RsnFlags' in properties:
            self.rsn_flags = properties['RsnFlags']
        if 'Mode' in properties:
            self.mode = properties['Mode']
        if 'Frequency' in properties:
            self.channel = frequency_to_channel(properties['Frequency'])

        self._initialized = True
        self.emit('props-changed', old_hash)

    def _get_all_props_error_cb(self, err):
        logging.error('Error getting the access point properties: %s', err)

    def _ap_properties_changed_cb(self, properties):
        self._update_properties(properties)

    def disconnect(self):
        self._bus.remove_signal_receiver(self._ap_properties_changed_cb,
                                         signal_name='PropertiesChanged',
                                         path=self.model.object_path,
                                         dbus_interface=NM_ACCESSPOINT_IFACE)


def get_manager():
    global _network_manager
    if _network_manager is None:
        obj = dbus.SystemBus().get_object(NM_SERVICE, NM_PATH)
        _network_manager = dbus.Interface(obj, NM_IFACE)
    return _network_manager


def _get_settings():
    global _nm_settings
    if _nm_settings is None:
        obj = dbus.SystemBus().get_object(NM_SERVICE, NM_SETTINGS_PATH)
        _nm_settings = dbus.Interface(obj, NM_SETTINGS_IFACE)
        _migrate_old_wifi_connections()
        _migrate_old_gsm_connection()
    return _nm_settings


def get_secret_agent():
    global _secret_agent
    if _secret_agent is None:
        _secret_agent = SecretAgent()
    return _secret_agent


def _activate_reply_cb(connection_path):
    logging.debug('Activated connection: %s', connection_path)


def _activate_error_cb(err):
    logging.error('Failed to activate connection: %s', err)


def _add_and_activate_reply_cb(settings_path, connection_path):
    logging.debug('Added and activated connection: %s', connection_path)


def _add_and_activate_error_cb(err):
    logging.error('Failed to add and activate connection: %s', err)


class Connection(GObject.GObject):
    __gsignals__ = {
        'removed': (GObject.SignalFlags.RUN_LAST, None, ()),
    }

    def __init__(self, bus, path):
        GObject.GObject.__init__(self)
        obj = bus.get_object(NM_SERVICE, path)
        self._connection = dbus.Interface(obj, NM_CONNECTION_IFACE)
        self._removed_handle = self._connection.connect_to_signal(
            'Removed', self._removed_cb)
        self._updated_handle = self._connection.connect_to_signal(
            'Updated', self._updated_cb)
        self._settings = self._connection.GetSettings(byte_arrays=True)

    def _updated_cb(self):
        self._settings = self._connection.GetSettings(byte_arrays=True)

    def _removed_cb(self):
        self._updated_handle.remove()
        self._removed_handle.remove()
        self.emit('removed')

    def get_settings(self, stype=None):
        if not stype:
            return self._settings
        elif stype in self._settings:
            return self._settings[stype]
        else:
            return None

    def get_secrets(self, stype, reply_handler, error_handler):
        return self._connection.GetSecrets(stype, byte_arrays=True,
                                           reply_handler=reply_handler,
                                           error_handler=error_handler)

    def update_settings(self, settings):
        self._connection.Update(settings)

    def activate(self, device_o, reply_handler=_activate_reply_cb,
                 error_handler=_activate_error_cb):
        activate_connection_by_path(self.get_path(), device_o,
                                    reply_handler=reply_handler,
                                    error_handler=error_handler)

    def delete(self):
        self._connection.Delete()

    def get_ssid(self):
        wifi_settings = self.get_settings('802-11-wireless')
        if wifi_settings and 'ssid' in wifi_settings:
            return wifi_settings['ssid']
        else:
            return None

    def get_id(self):
        return self.get_settings('connection')['id']

    def get_path(self):
        return self._connection.object_path


class Connections(object):

    def __init__(self):
        self._bus = dbus.SystemBus()
        self._connections = []

        settings = _get_settings()
        settings.connect_to_signal('NewConnection', self._new_connection_cb)

        for connection_o in settings.ListConnections():
            self._monitor_connection(connection_o)

    def get_list(self):
        return self._connections

    def _monitor_connection(self, connection_o):
        connection = Connection(self._bus, connection_o)
        connection.connect('removed', self._connection_removed_cb)
        self._connections.append(connection)

    def _new_connection_cb(self, connection_o):
        self._monitor_connection(connection_o)

    def _connection_removed_cb(self, connection):
        connection.disconnect_by_func(self._connection_removed_cb)
        self._connections.remove(connection)


def get_wireless_interfaces():
    global _interfaces
    if _interfaces is None:

        _interfaces = []
        bus = dbus.SystemBus()
        for device_path in get_manager().GetDevices():
            device_object = bus.get_object(NM_SERVICE, device_path)
            properties = dbus.Interface(device_object,
                                        'org.freedesktop.DBus.Properties')
            device_type = properties.Get(NM_DEVICE_IFACE, 'DeviceType')
            if device_type != NM_DEVICE_TYPE_WIFI:
                continue

            _interfaces.append(properties.Get(NM_DEVICE_IFACE, 'Interface'))
    return _interfaces


def get_connections():
    global _connections
    if _connections is None:
        _connections = Connections()
    return _connections


def find_connection_by_ssid(ssid):
    # FIXME: this check should be more extensive.
    # it should look at mode (infra/adhoc), band, security, and really
    # anything that is stored in the settings.
    for connection in get_connections().get_list():
        if connection.get_ssid() == ssid:
            return connection
    return None


def find_connection_by_id(connection_id):
    for connection in get_connections().get_list():
        if connection.get_id() == connection_id:
            return connection
    return None


def _add_connection_reply_cb(connection):
    logging.debug('Added connection: %s', connection)


def _add_connection_error_cb(err):
    logging.error('Failed to add connection: %s', err)


def add_connection(settings, reply_handler=_add_connection_reply_cb,
                   error_handler=_add_connection_error_cb):
    _get_settings().AddConnection(settings.get_dict(),
                                  reply_handler=reply_handler,
                                  error_handler=error_handler)


def activate_connection_by_path(connection, device_o,
                                reply_handler=_activate_reply_cb,
                                error_handler=_activate_error_cb):
    get_manager().ActivateConnection(connection,
                                     device_o,
                                     '/',
                                     reply_handler=reply_handler,
                                     error_handler=error_handler)


def add_and_activate_connection(device_o, settings, specific_object):
    manager = get_manager()
    manager.AddAndActivateConnection(settings.get_dict(), device_o,
                                     specific_object,
                                     reply_handler=_add_and_activate_reply_cb,
                                     error_handler=_add_and_activate_error_cb)


def _migrate_old_wifi_connections():
    """Migrate connections.cfg from Sugar-0.94 and previous to NetworkManager
    system-wide connections
    """

    profile_path = env.get_profile_path()
    config_path = os.path.join(profile_path, 'nm', 'connections.cfg')
    if not os.path.exists(config_path):
        return

    config = ConfigParser.ConfigParser()
    try:
        if not config.read(config_path):
            logging.error('Error reading the nm config file')
            return
    except ConfigParser.ParsingError:
        logging.exception('Error reading the nm config file')
        return

    for section in config.sections():
        try:
            settings = Settings()
            settings.connection.id = section
            ssid = config.get(section, 'ssid')
            settings.wireless.ssid = dbus.ByteArray(ssid)
            config_uuid = config.get(section, 'uuid')
            settings.connection.uuid = config_uuid
            nmtype = config.get(section, 'type')
            settings.connection.type = nmtype
            autoconnect = bool(config.get(section, 'autoconnect'))
            settings.connection.autoconnect = autoconnect

            if config.has_option(section, 'timestamp'):
                timestamp = int(config.get(section, 'timestamp'))
                settings.connection.timestamp = timestamp

            if config.has_option(section, 'key-mgmt'):
                settings.wireless_security = WirelessSecurity()
                mgmt = config.get(section, 'key-mgmt')
                settings.wireless_security.key_mgmt = mgmt
                security = config.get(section, 'security')
                settings.wireless.security = security
                key = config.get(section, 'key')
                if mgmt == 'none':
                    settings.wireless_security.wep_key = key
                    auth_alg = config.get(section, 'auth-alg')
                    settings.wireless_security.auth_alg = auth_alg
                elif mgmt == 'wpa-psk':
                    settings.wireless_security.psk = key
                    if config.has_option(section, 'proto'):
                        value = config.get(section, 'proto')
                        settings.wireless_security.proto = value
                    if config.has_option(section, 'group'):
                        value = config.get(section, 'group')
                        settings.wireless_security.group = value
                    if config.has_option(section, 'pairwise'):
                        value = config.get(section, 'pairwise')
                        settings.wireless_security.pairwise = value
        except ConfigParser.Error:
            logging.exception('Error reading section')
        else:
            add_connection(settings)

    os.unlink(config_path)


def create_gsm_connection(username, password, number, apn, pin):
    settings = SettingsGsm()
    settings.gsm.username = username
    settings.gsm.number = number
    settings.gsm.apn = apn
    settings.gsm.pin = pin
    settings.gsm.password = password

    settings.connection.id = GSM_CONNECTION_ID
    settings.connection.type = NM_CONNECTION_TYPE_GSM
    settings.connection.uuid = str(uuid.uuid4())
    settings.connection.autoconnect = False
    settings.ip4_config.method = 'auto'
    settings.serial.baud = GSM_BAUD_RATE

    add_connection(settings)


def _migrate_old_gsm_connection():
    if find_gsm_connection():
        # don't attempt migration if a NM-level connection already exists
        return

    settings = Gio.Settings(GSM_KEYS_PATH)

    username = settings.get_string(GSM_USERNAME_KEY) or ''
    password = settings.get_string(GSM_PASSWORD_KEY) or ''
    number = settings.get_string(GSM_NUMBER_KEY) or ''
    apn = settings.get_string(GSM_APN_KEY) or ''
    pin = settings.get_string(GSM_PIN_KEY) or ''

    if apn or number:
        logging.info("Migrating old GSM connection details")
        try:
            create_gsm_connection(username, password, number, apn, pin)
            # remove old connection
            for setting in (GSM_USERNAME_KEY, GSM_PASSWORD_KEY,
                            GSM_NUMBER_KEY, GSM_APN_KEY, GSM_PIN_KEY,
                            GSM_PUK_KEY):
                settings.set_string(setting, '')
        except Exception:
            logging.exception('Error adding gsm connection to NMSettings.')


def find_gsm_connection():
    return find_connection_by_id(GSM_CONNECTION_ID)


def disconnect_access_points(ap_paths):
    """
    Disconnect all devices connected to any of the given access points.
    """
    bus = dbus.SystemBus()
    netmgr_obj = bus.get_object(NM_SERVICE, NM_PATH)
    netmgr = dbus.Interface(netmgr_obj, NM_IFACE)
    netmgr_props = dbus.Interface(netmgr, dbus.PROPERTIES_IFACE)
    active_connection_paths = netmgr_props.Get(NM_IFACE, 'ActiveConnections')

    for conn_path in active_connection_paths:
        conn_obj = bus.get_object(NM_IFACE, conn_path)
        conn_props = dbus.Interface(conn_obj, dbus.PROPERTIES_IFACE)
        ap_path = conn_props.Get(NM_ACTIVE_CONN_IFACE, 'SpecificObject')
        if ap_path == '/' or ap_path not in ap_paths:
            continue

        dev_paths = conn_props.Get(NM_ACTIVE_CONN_IFACE, 'Devices')
        for dev_path in dev_paths:
            dev_obj = bus.get_object(NM_SERVICE, dev_path)
            dev = dbus.Interface(dev_obj, NM_DEVICE_IFACE)
            dev.Disconnect()


def forget_wireless_network(ssid):
    connection = find_connection_by_ssid(ssid)
    if connection:
        connection.delete()


def _is_non_printable(char):
    """
    Return True if char is a non-printable unicode character, False otherwise
    """
    return (char < u' ') or (u'~' < char < u'\xA0') or (char == u'\xAD')


def ssid_to_display_name(ssid):
    """Convert an SSID into a unicode string for recognising Access Points

    Return a unicode string that's useful for recognising and
    distinguishing between Access Points (APs).

    IEEE 802.11 defines SSIDs as arbitrary byte sequences. As random
    bytes are not very user-friendly, most APs use some human-readable
    character string as SSID. However, because there's no standard
    specifying what encoding to use, AP vendors chose various
    different encodings. Since there's also no indication of what
    encoding was used for a particular SSID, the best we can do for
    turning an SSID into a displayable string is to try a couple of
    encodings based on some heuristic.

    We're currently using the following heuristic:

    1. If the SSID is a valid character string consisting only of
       printable characters in one of the following encodings (tried in
       the given order), decode it accordingly:
       UTF-8, ISO-8859-1, Windows-1251.
    2. Return a hex dump of the SSID.
    """
    for encoding in ['utf-8', 'iso-8859-1', 'windows-1251']:
        try:
            display_name = unicode(ssid, encoding)
        except UnicodeDecodeError:
            continue

        if not [True for char in display_name if _is_non_printable(char)]:
            # Only printable characters
            return display_name

    return ':'.join(['%02x' % (ord(byte), ) for byte in ssid])


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
        NM_CONNECTION_TYPE_802_11_WIRELESS)
    if wifi_settings:
        return not (wifi_settings['mode'] == 'adhoc' and
                    connection.get_id() in wifi_whitelist)

    mesh_settings = connection.get_settings(
        NM_CONNECTION_TYPE_802_11_OLPC_MESH)
    if mesh_settings:
        return not connection.get_id() in mesh_whitelist


def clear_wireless_networks():
    """Remove all wireless connections except Sugar-internal ones.
    """
    try:
        connections = get_connections()
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
        connections = get_connections()
    except dbus.DBusException:
        logging.debug('NetworkManager not available')
        return False
    else:
        return any(is_wireless(connection)
                   for connection in connections.get_list())
