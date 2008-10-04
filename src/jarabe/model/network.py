#
# Copyright (C) 2006-2008 Red Hat, Inc.
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

import time
import os
import binascii
import ConfigParser
import logging

import dbus
import dbus.glib
import dbus.decorators
import gobject

from sugar.graphics import xocolor
from sugar import env

IW_AUTH_ALG_OPEN_SYSTEM = 0x00000001
IW_AUTH_ALG_SHARED_KEY  = 0x00000002

NM_DEVICE_STAGE_STRINGS = ("Unknown",
                           "Prepare",
                           "Config",
                           "Need Users Key",
                           "IP Config",
                           "IP Config Get",
                           "IP Config Commit",
                           "Activated",
                           "Failed",
                           "Canceled"
                           )

NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_IFACE = 'org.freedesktop.NetworkManager'
NM_IFACE_DEVICES = 'org.freedesktop.NetworkManager.Devices'
NM_PATH = '/org/freedesktop/NetworkManager'

DEVICE_TYPE_UNKNOWN = 0
DEVICE_TYPE_802_3_ETHERNET = 1
DEVICE_TYPE_802_11_WIRELESS = 2
DEVICE_TYPE_802_11_MESH_OLPC = 3

NM_DEVICE_CAP_NONE = 0x00000000
NM_DEVICE_CAP_NM_SUPPORTED = 0x00000001
NM_DEVICE_CAP_CARRIER_DETECT = 0x00000002
NM_DEVICE_CAP_WIRELESS_SCAN = 0x00000004

NM_802_11_CAP_NONE            = 0x00000000
NM_802_11_CAP_PROTO_NONE      = 0x00000001
NM_802_11_CAP_PROTO_WEP       = 0x00000002
NM_802_11_CAP_PROTO_WPA       = 0x00000004
NM_802_11_CAP_PROTO_WPA2      = 0x00000008
NM_802_11_CAP_KEY_MGMT_PSK    = 0x00000040
NM_802_11_CAP_KEY_MGMT_802_1X = 0x00000080
NM_802_11_CAP_CIPHER_WEP40    = 0x00001000
NM_802_11_CAP_CIPHER_WEP104   = 0x00002000
NM_802_11_CAP_CIPHER_TKIP     = 0x00004000
NM_802_11_CAP_CIPHER_CCMP     = 0x00008000

NETWORK_STATE_CONNECTING   = 0
NETWORK_STATE_CONNECTED    = 1
NETWORK_STATE_NOTCONNECTED = 2

DEVICE_STATE_ACTIVATING = 0
DEVICE_STATE_ACTIVATED  = 1
DEVICE_STATE_INACTIVE   = 2

IW_MODE_ADHOC = 1
IW_MODE_INFRA = 2

IW_AUTH_KEY_MGMT_802_1X = 0x1
IW_AUTH_KEY_MGMT_PSK = 0x2

IW_AUTH_WPA_VERSION_DISABLED = 0x00000001
IW_AUTH_WPA_VERSION_WPA      = 0x00000002
IW_AUTH_WPA_VERSION_WPA2     = 0x00000004

NM_AUTH_TYPE_WPA_PSK_AUTO = 0x00000000
IW_AUTH_CIPHER_NONE   = 0x00000001
IW_AUTH_CIPHER_WEP40  = 0x00000002
IW_AUTH_CIPHER_TKIP   = 0x00000004
IW_AUTH_CIPHER_CCMP   = 0x00000008
IW_AUTH_CIPHER_WEP104 = 0x00000010

IW_AUTH_ALG_OPEN_SYSTEM = 0x00000001
IW_AUTH_ALG_SHARED_KEY  = 0x00000002

NETWORK_TYPE_UNKNOWN = 0
NETWORK_TYPE_ALLOWED = 1
NETWORK_TYPE_INVALID = 2

sys_bus = dbus.SystemBus()

class NetworkInvalidError(Exception):
    pass

class NotFoundError(dbus.DBusException):
    pass

class UnsupportedError(dbus.DBusException):
    pass

class NMConfig(ConfigParser.ConfigParser):
    def get_bool(self, section, name):
        opt = self.get(section, name)
        if type(opt) == str:
            if opt.lower() == 'yes' or opt.lower() == 'true':
                return True
            elif opt.lower() == 'no' or opt.lower() == 'false':
                return False
        raise ValueError("Invalid format for %s/%s.  Should be one of" \
                         " [yes, no, true, false]." % (section, name))

    def get_list(self, section, name):
        opt = self.get(section, name)
        if type(opt) != str or not len(opt):
            return []
        try:
            return opt.split()
        except Exception:
            raise ValueError("Invalid format for %s/%s.  Should be a" \
                             " space-separate list." % (section, name))

    def get_int(self, section, name):
        opt = self.get(section, name)
        try:
            return int(opt)
        except ValueError:
            raise ValueError("Invalid format for %s/%s.  Should be a" \
                             " valid integer." % (section, name))

    def get_float(self, section, name):
        opt = self.get(section, name)
        try:
            return float(opt)
        except ValueError:
            raise ValueError("Invalid format for %s/%s.  Should be a" \
                             " valid float." % (section, name))

class Security(object):
    def __init__(self, we_cipher):
        self._we_cipher = we_cipher
        self._key = None
        self._auth_alg = None

    def read_from_config(self, cfg, name):
        pass

    def read_from_args(self, args):
        pass

    def new_from_config(cfg, name):
        security = None
        we_cipher = cfg.get_int(name, "we_cipher")
        if we_cipher == IW_AUTH_CIPHER_NONE:
            security = Security(we_cipher)
        elif we_cipher == IW_AUTH_CIPHER_WEP40 or \
                        we_cipher == IW_AUTH_CIPHER_WEP104:
            security = WEPSecurity(we_cipher)
        elif we_cipher == NM_AUTH_TYPE_WPA_PSK_AUTO or \
                        we_cipher == IW_AUTH_CIPHER_CCMP or \
                        we_cipher == IW_AUTH_CIPHER_TKIP:
            security = WPASecurity(we_cipher)
        else:
            raise ValueError("Unsupported security combo")
        security.read_from_config(cfg, name)
        return security
    new_from_config = staticmethod(new_from_config)

    def new_from_args(we_cipher, args):
        security = None
        try:
            if we_cipher == IW_AUTH_CIPHER_NONE:
                security = Security(we_cipher)
            elif we_cipher == IW_AUTH_CIPHER_WEP40 or \
                            we_cipher == IW_AUTH_CIPHER_WEP104:
                security = WEPSecurity(we_cipher)
            elif we_cipher == NM_AUTH_TYPE_WPA_PSK_AUTO or \
                            we_cipher == IW_AUTH_CIPHER_CCMP or \
                            we_cipher == IW_AUTH_CIPHER_TKIP:
                security = WPASecurity(we_cipher)
            else:
                raise ValueError("Unsupported security combo")
            security.read_from_args(args)
        except ValueError, e:
            logging.debug("Error reading security information: %s" % e)
            del security
            return None
        return security
    new_from_args = staticmethod(new_from_args)

    def get_properties(self):
        return [dbus.Int32(self._we_cipher)]

    def write_to_config(self, section, config):
        config.set(section, "we_cipher", self._we_cipher)


class WEPSecurity(Security):
    def read_from_args(self, args):
        if len(args) != 2:
            raise ValueError("not enough arguments")
        key = args[0]
        auth_alg = args[1]
        if isinstance(key, unicode):
            key = key.encode()
        if not isinstance(key, str):
            raise ValueError("wrong argument type for key")
        if not isinstance(auth_alg, int):
            raise ValueError("wrong argument type for auth_alg")
        self._key = key
        self._auth_alg = auth_alg

    def read_from_config(self, cfg, name):
        # Key should be a hex encoded string
        self._key = cfg.get(name, "key")
        if self._we_cipher == IW_AUTH_CIPHER_WEP40 and len(self._key) != 10:
            raise ValueError("Key length not right for 40-bit WEP")
        if self._we_cipher == IW_AUTH_CIPHER_WEP104 and len(self._key) != 26:
            raise ValueError("Key length not right for 104-bit WEP")

        try:
            binascii.a2b_hex(self._key)
        except TypeError:
            raise ValueError("Key was not a hexadecimal string.")
            
        self._auth_alg = cfg.get_int(name, "auth_alg")
        if self._auth_alg != IW_AUTH_ALG_OPEN_SYSTEM and \
                self._auth_alg != IW_AUTH_ALG_SHARED_KEY:
            raise ValueError("Invalid authentication algorithm %d"
                             % self._auth_alg)

    def get_properties(self):
        args = Security.get_properties(self)
        args.append(dbus.String(self._key))
        args.append(dbus.Int32(self._auth_alg))
        return args

    def write_to_config(self, section, config):
        Security.write_to_config(self, section, config)
        config.set(section, "key", self._key)
        config.set(section, "auth_alg", self._auth_alg)

class WPASecurity(Security):
    def __init__(self, we_cipher):
        Security.__init__(self, we_cipher)
        self._wpa_ver = None
        self._key_mgmt = None

    def read_from_args(self, args):
        if len(args) != 3:
            raise ValueError("not enough arguments")
        key = args[0]
        if isinstance(key, unicode):
            key = key.encode()
        if not isinstance(key, str):
            raise ValueError("wrong argument type for key")

        wpa_ver = args[1]
        if not isinstance(wpa_ver, int):
            raise ValueError("wrong argument type for WPA version")

        key_mgmt = args[2]
        if not isinstance(key_mgmt, int):
            raise ValueError("wrong argument type for WPA key management")
        if not key_mgmt & IW_AUTH_KEY_MGMT_PSK:
            raise ValueError("Key management types other than" \
                             " PSK are not supported")

        self._key = key
        self._wpa_ver = wpa_ver
        self._key_mgmt = key_mgmt

    def read_from_config(self, cfg, name):
        # Key should be a hex encoded string
        self._key = cfg.get(name, "key")
        if len(self._key) != 64:
            raise ValueError("Key length not right for WPA-PSK")

        try:
            binascii.a2b_hex(self._key)
        except TypeError:
            raise ValueError("Key was not a hexadecimal string.")
            
        self._wpa_ver = cfg.get_int(name, "wpa_ver")
        if self._wpa_ver != IW_AUTH_WPA_VERSION_WPA and \
                self._wpa_ver != IW_AUTH_WPA_VERSION_WPA2:
            raise ValueError("Invalid WPA version %d" % self._wpa_ver)

        self._key_mgmt = cfg.get_int(name, "key_mgmt")
        if not self._key_mgmt & IW_AUTH_KEY_MGMT_PSK:
            raise ValueError("Invalid WPA key management option %d"
                             % self._key_mgmt)

    def get_properties(self):
        args = Security.get_properties(self)
        args.append(dbus.String(self._key))
        args.append(dbus.Int32(self._wpa_ver))
        args.append(dbus.Int32(self._key_mgmt))
        return args

    def write_to_config(self, section, config):
        Security.write_to_config(self, section, config)
        config.set(section, "key", self._key)
        config.set(section, "wpa_ver", self._wpa_ver)
        config.set(section, "key_mgmt", self._key_mgmt)


class NetworkInfo:
    def __init__(self, ssid):
        self.ssid = ssid
        self.timestamp = int(time.time())
        self.bssids = []
        self.we_cipher = 0
        self._security = None

    def get_properties(self):
        bssid_list = dbus.Array([], signature="s")
        for item in self.bssids:
            bssid_list.append(dbus.String(item))
        args = [dbus.String(self.ssid), dbus.Int32(self.timestamp),
                dbus.Boolean(True), bssid_list]
        args += self._security.get_properties()
        return tuple(args)

    def get_security(self):
        return self._security.get_properties()

    def set_security(self, security):
        self._security = security

    def read_from_args(self, auto, bssid, we_cipher, args):
        if auto == False:
            self.timestamp = int(time.time())
        if not bssid in self.bssids:
            self.bssids.append(bssid)

        self._security = Security.new_from_args(we_cipher, args)
        if not self._security:
            raise NetworkInvalidError("Invalid security information")

    def read_from_config(self, config):
        try:
            self.timestamp = config.get_int(self.ssid, "timestamp")
        except (ConfigParser.NoOptionError, ValueError), e:
            raise NetworkInvalidError(e)

        try:
            self._security = Security.new_from_config(config, self.ssid)
        except Exception, e:
            raise NetworkInvalidError(e)

        # The following don't need to be present
        try:
            self.bssids = config.get_list(self.ssid, "bssids")
        except (ConfigParser.NoOptionError, ValueError), e:
            logging.debug("Error reading bssids: %s" % e)

    def write_to_config(self, config):
        try:
            config.add_section(self.ssid)
            config.set(self.ssid, "timestamp", self.timestamp)
            if len(self.bssids) > 0:
                opt = " "
                opt = opt.join(self.bssids)
                config.set(self.ssid, "bssids", opt)
            self._security.write_to_config(self.ssid, config)
        except Exception, e:
            logging.debug("Error writing '%s': %s" % (self.ssid, e))

class NMInfo(object):
    def __init__(self, client):
        profile_path = env.get_profile_path()
        self._cfg_file = os.path.join(profile_path, "nm", "networks.cfg")
        self._nmclient = client

        self.allowed_networks = self._read_config()

    def save_config(self):
        self._write_config(self.allowed_networks)

    def _read_config(self):
        if not os.path.exists(os.path.dirname(self._cfg_file)):
            os.makedirs(os.path.dirname(self._cfg_file), 0755)
        if not os.path.exists(self._cfg_file):
            self._write_config({})
            return {}

        config = NMConfig()
        config.read(self._cfg_file)
        networks = {}
        for name in config.sections():
            try:
                net = NetworkInfo(name)
                net.read_from_config(config)
                networks[name] = net
            except Exception, e:
                logging.error("Error when processing config for" \
                              " the network %s: %r" % (name, e))

        del config
        return networks

    def _write_config(self, networks):
        fp = open(self._cfg_file, 'w')
        config = NMConfig()
        for net in networks.values():
            net.write_to_config(config)
        config.write(fp)
        fp.close()
        del config

    def get_networks(self, net_type):
        if net_type != NETWORK_TYPE_ALLOWED:
            raise ValueError("Bad network type")
        nets = []
        for net in self.allowed_networks.values():
            nets.append(net.ssid)
        logging.debug("Returning networks: %s" % nets)
        return nets

    def get_network_properties(self, ssid, net_type, async_cb, async_err_cb):
        if not isinstance(ssid, unicode):
            async_err_cb(ValueError("Invalid arguments; ssid must be unicode."))
        if net_type != NETWORK_TYPE_ALLOWED:
            async_err_cb(ValueError("Bad network type"))
        if not self.allowed_networks.has_key(ssid):
            async_err_cb(NotFoundError("Network '%s' not found." % ssid))
        network = self.allowed_networks[ssid]
        props = network.get_properties()

        # DBus workaround: the normal method return handler wraps
        # the returned arguments in a tuple and then converts that to a
        # struct, but NetworkManager expects a plain list of arguments.
        # It turns out that the async callback method return code _doesn't_
        # wrap the returned arguments in a tuple, so as a workaround use
        # the async callback stuff here even though we're not doing it
        # asynchronously.
        async_cb(*props)

    def update_network_info(self, ssid, auto, bssid, we_cipher, args):
        if not isinstance(ssid, unicode):
            raise ValueError("Invalid arguments; ssid must be unicode.")
        if self.allowed_networks.has_key(ssid):
            del self.allowed_networks[ssid]
        net = Network(ssid)
        try:
            net.read_from_args(auto, bssid, we_cipher, args)
            logging.debug("Updated network information for '%s'." % ssid)
            self.allowed_networks[ssid] = net
            self.save_config()
        except NetworkInvalidError, e:
            logging.debug("Error updating network information: %s" % e)
            del net

    # this method is invoked directly in-process (not by DBus).
    def delete_all_networks(self):
        self.allowed_networks = {}
        self.save_config()

class Network(gobject.GObject):
    __gsignals__ = {
        'initialized'     : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([gobject.TYPE_BOOLEAN])),
        'strength-changed': (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([])),
        'state-changed'   : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([]))
    }

    def __init__(self, client, op):
        gobject.GObject.__init__(self)
        self._client = client
        self._op = op
        self._ssid = None
        self._mode = None
        self._strength = 0
        self._caps = 0
        self._valid = False
        self._favorite = False
        self._state = NETWORK_STATE_NOTCONNECTED

        obj = sys_bus.get_object(NM_SERVICE, self._op)
        net = dbus.Interface(obj, NM_IFACE_DEVICES)
        net.getProperties(reply_handler=self._update_reply_cb,
                error_handler=self._update_error_cb)

    def _update_reply_cb(self, *props):
        self._ssid = props[1]
        self._strength = props[3]
        self._mode = props[6]
        self._caps = props[7]
        if self._caps & NM_802_11_CAP_PROTO_WPA or \
                self._caps & NM_802_11_CAP_PROTO_WPA2:
            if not (self._caps & NM_802_11_CAP_KEY_MGMT_PSK):
                # 802.1x is not supported at this time
                logging.debug("Net(%s): ssid '%s' dropping because 802.1x" \
                              "is unsupported" % (self._op, self._ssid))
                self._valid = False
                self.emit('initialized', self._valid)
                return
        if self._mode != IW_MODE_INFRA:
            # Don't show Ad-Hoc networks; they usually don't DHCP and therefore
            # won't work well here.  This also works around the bug where
            # we show our own mesh SSID on the Mesh view when in mesh mode
            logging.debug("Net(%s): ssid '%s' is adhoc; not showing" %
                          (self._op, self._ssid))
            self._valid = False
            self.emit('initialized', self._valid)
            return

        fav_nets = []
        if self._client.nminfo:
            fav_nets = self._client.nminfo.get_networks(NETWORK_TYPE_ALLOWED)
        if self._ssid in fav_nets:
            self._favorite = True

        self._valid = True
        logging.debug("Net(%s): caps 0x%X" % (self._ssid, self._caps))
        self.emit('initialized', self._valid)

    def _update_error_cb(self, err):
        logging.debug("Net(%s): failed to update. (%s)" % (self._op, err))
        self._valid = False
        self.emit('initialized', self._valid)

    def get_colors(self):
        import sha
        sh = sha.new()
        data = self._ssid + hex(self._caps) + hex(self._mode)
        sh.update(data)
        h = hash(sh.digest())
        idx = h % len(xocolor.colors)
        # stroke, fill
        return (xocolor.colors[idx][0], xocolor.colors[idx][1])

    def get_ssid(self):
        return self._ssid

    def get_caps(self):
        return self._caps

    def get_mode(self):
        return self._mode

    def get_state(self):
        return self._state

    def set_state(self, state):
        if state == self._state:
            return
        self._state = state
        if self._valid:
            self.emit('state-changed')

    def get_op(self):
        return self._op

    def get_strength(self):
        return self._strength

    def set_strength(self, strength):
        if strength == self._strength:
            return
        self._strength = strength
        if self._valid:
            self.emit('strength-changed')

    def is_valid(self):
        return self._valid

    def is_favorite(self):
        return self._favorite

class Device(gobject.GObject):
    __gsignals__ = {
        'initialized':              (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE, ([])),
        'init-failed':              (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE, ([])),
        'ssid-changed':             (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE, ([])),
        'strength-changed':         (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE, ([])),
        'state-changed':            (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE, ([])),
        'activation-stage-changed': (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE, ([])),
        'network-appeared':         (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE,
                                     ([gobject.TYPE_PYOBJECT])),
        'network-disappeared':      (gobject.SIGNAL_RUN_FIRST,
                                     gobject.TYPE_NONE,
                                     ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, client, op):
        gobject.GObject.__init__(self)
        self._client = client
        self._op = op
        self._iface = None
        self._type = DEVICE_TYPE_UNKNOWN
        self._udi = None
        self._active = False
        self._act_stage = 0
        self._strength = 0
        self._freq = 0.0
        self._link = False
        self._valid = False
        self._networks = {}
        self._caps = 0
        self._state = DEVICE_STATE_INACTIVE
        self._active_network = None
        self._active_net_sigid = 0

        obj = sys_bus.get_object(NM_SERVICE, self._op)
        self.dev = dbus.Interface(obj, NM_IFACE_DEVICES)
        self.dev.getProperties(reply_handler=self._update_reply_cb,
                error_handler=self._update_error_cb)

    def _is_activating(self):
        if self._active and self._act_stage >= 1 and self._act_stage <= 6:
            return True
        return False

    def _is_activated(self):
        if self._active and self._act_stage == 7:
            return True
        return False

    def _update_reply_cb(self, *props):
        self._iface = props[1]
        self._type = props[2]
        self._udi = props[3]
        self._active = props[4]
        self._act_stage = props[5]
        self._link = props[15]
        self._caps = props[17]

        if self._type == DEVICE_TYPE_802_11_WIRELESS:
            old_strength = self._strength
            self._strength = props[14]
            if self._strength != old_strength:
                if self._valid:
                    self.emit('strength-changed')
            self._update_networks(props[20], props[19])
        elif self._type ==  DEVICE_TYPE_802_11_MESH_OLPC:
            old_strength = self._strength
            self._strength = props[14]
            if self._strength != old_strength:
                if self._valid:
                    self.emit('strength-changed')

        self._valid = True

        if self._is_activating():
            self.set_state(DEVICE_STATE_ACTIVATING)
        elif self._is_activated():
            self.set_state(DEVICE_STATE_ACTIVATED)
        else:
            self.set_state(DEVICE_STATE_INACTIVE)

        self.emit('initialized')

    def _update_networks(self, net_ops, active_op):
        for op in net_ops:
            net = Network(self._client, op)
            self._networks[op] = net
            net.connect('initialized', lambda *args:
                        self._net_initialized_cb(active_op, *args))

    def _update_error_cb(self, err):
        logging.debug("Device(%s): failed to update. (%s)" % (self._op, err))
        self._valid = False
        self.emit('init-failed')

    def _net_initialized_cb(self, active_op, net, valid):
        net_op = net.get_op()
        if not self._networks.has_key(net_op):
            return

        if not valid:
            # init failure
            del self._networks[net_op]
            return

        # init success
        if self._valid:
            self.emit('network-appeared', net)
        if active_op and net_op == active_op:
            self.set_active_network(net)

    def get_op(self):
        return self._op

    def get_networks(self):
        ret = []
        for net in self._networks.values():
            if net.is_valid():
                ret.append(net)
        return ret

    def get_network(self, op):
        if self._networks.has_key(op) and self._networks[op].is_valid():
            return self._networks[op]
        return None

    def get_network_ops(self):
        ret = []
        for net in self._networks.values():
            if net.is_valid():
                ret.append(net.get_op())
        return ret

    def get_mesh_step(self):
        if self._type !=  DEVICE_TYPE_802_11_MESH_OLPC:
            raise RuntimeError("Only valid for mesh devices")
        try:
            step = self.dev.getMeshStep(timeout=3)
        except dbus.DBusException:
            step = 0
        return step

    def get_frequency(self):
        try:
            freq = self.dev.getFrequency(timeout=3)
        except dbus.DBusException:
            freq = 0.0
        # Hz -> GHz
        self._freq = freq / 1000000000.0
        return self._freq

    def get_strength(self):
        return self._strength

    def set_strength(self, strength):
        if strength == self._strength:
            return False

        if strength >= 0 and strength <= 100:
            self._strength = strength
        else:
            self._strength = 0

        if self._valid:
            self.emit('strength-changed')

    def network_appeared(self, network):
        # NM may emit NetworkAppeared messages before the initialization-time
        # getProperties call completes. This means that we are in danger of
        # instantiating the "appeared" network here, and then instantiating
        # the same network later on when getProperties completes
        # (_update_reply_cb calls _update_networks).
        # We avoid this race by confirming that getProperties has completed
        # before listening to any NetworkAppeared messages. We assume that
        # any networks that get reported as appeared in this race window
        # will be included in the getProperties response.
        if not self._valid:
            return

        if self._networks.has_key(network):
            return
        net = Network(self._client, network)
        self._networks[network] = net
        net.connect('initialized', lambda *args:
                    self._net_initialized_cb(None, *args))

    def network_disappeared(self, network):
        if not self._networks.has_key(network):
            return

        if self._valid:
            self.emit('network-disappeared', self._networks[network])

        del self._networks[network]

    def set_active_network(self, network):
        if self._active_network == network:
            return

        # Make sure the old one doesn't get a stuck state
        if self._active_network:
            self._active_network.set_state(NETWORK_STATE_NOTCONNECTED)
            self._active_network.disconnect(self._active_net_sigid)

        self._active_network = network

        if self._active_network:
            self._active_net_sigid = self._active_network.connect(
                    "initialized", self._active_net_initialized)

        # don't emit ssid-changed for networks that are not yet valid
        if self._valid:
            if self._active_network and self._active_network.is_valid():
                self.emit('ssid-changed')
            elif not self._active_network:
                self.emit('ssid-changed')

    def _active_net_initialized(self, net, user_data=None):
        if self._active_network and self._active_network.is_valid():
            self.emit('ssid-changed')

    def _get_active_net_cb(self, state, net_op):
        if not self._networks.has_key(net_op):
            self.set_active_network(None)
            return

        self.set_active_network(self._networks[net_op])

        _device_to_network_state = {
            DEVICE_STATE_ACTIVATING : NETWORK_STATE_CONNECTING,
            DEVICE_STATE_ACTIVATED  : NETWORK_STATE_CONNECTED,
            DEVICE_STATE_INACTIVE   : NETWORK_STATE_NOTCONNECTED
        }

        network_state = _device_to_network_state[state]
        self._active_network.set_state(network_state)

    def _get_active_net_error_cb(self, err):
        logging.debug("Couldn't get active network: %s" % err)
        self.set_active_network(None)

    def get_state(self):
        return self._state

    def set_state(self, state):
        if state == self._state:
            return

        if state == DEVICE_STATE_INACTIVE:
            self._act_stage = 0

        self._state = state
        if self._valid:
            self.emit('state-changed')

        if self._type == DEVICE_TYPE_802_11_WIRELESS:
            if state == DEVICE_STATE_INACTIVE:
                self.set_active_network(None)
            else:
                self.dev.getActiveNetwork(
                    reply_handler=lambda *args:
                    self._get_active_net_cb(state, *args),
                    error_handler=self._get_active_net_error_cb)

    def set_activation_stage(self, stage):
        if stage == self._act_stage:
            return
        self._act_stage = stage
        if self._valid:
            self.emit('activation-stage-changed')

    def get_activation_stage(self):
        return self._act_stage

    def get_ssid(self):
        if self._active_network and self._active_network.is_valid():
            return self._active_network.get_ssid()
        elif not self._active_network:
            return None

    def get_active_network(self):
        return self._active_network

    def get_type(self):
        return self._type

    def is_valid(self):
        return self._valid

    def set_carrier(self, on):
        self._link = on

    def get_capabilities(self):
        return self._caps

class NMClient(gobject.GObject):
    __gsignals__ = {
        'device-added'     : (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT])),
        'device-activated' : (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT])),
        'device-activating': (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT])),
        'device-removed'   : (gobject.SIGNAL_RUN_FIRST,
                              gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self.nminfo = None
        self._nm_present = False
        self._nm_proxy = None
        self._nm_obj = None
        self._sig_handlers = None
        self._update_timer = 0
        self._devices = {}

        self.nminfo = NMInfo(self)
        
        self._setup_dbus()
        if self._nm_present:
            self._get_initial_devices()

    def get_devices(self):
        return self._devices.values()

    def _get_initial_devices_reply_cb(self, ops):
        for op in ops:
            self._add_device(op)

    def _dev_initialized_cb(self, dev):
        self.emit('device-added', dev)

    def _dev_init_failed_cb(self, dev):
        # Device failed to initialize, likely due to dbus errors or something
        op = dev.get_op()
        self._remove_device(op)

    def _get_initial_devices_error_cb(self, err):
        logging.debug("Error updating devices (%s)" % err)

    def _get_initial_devices(self):
        self._nm_obj.getDevices(
            reply_handler=self._get_initial_devices_reply_cb,
            error_handler=self._get_initial_devices_error_cb)

    def _add_device(self, dev_op):
        if self._devices.has_key(dev_op):
            return
        dev = Device(self, dev_op)
        self._devices[dev_op] = dev
        dev.connect('init-failed', self._dev_init_failed_cb)
        dev.connect('initialized', self._dev_initialized_cb)
        dev.connect('state-changed', self._dev_state_changed_cb)

    def _remove_device(self, dev_op):
        if not self._devices.has_key(dev_op):
            return
        dev = self._devices[dev_op]
        if dev.is_valid():
            self.emit('device-removed', dev)
        del self._devices[dev_op]

    def _dev_state_changed_cb(self, dev):
        op = dev.get_op()
        if not self._devices.has_key(op) or not dev.is_valid():
            return
        if dev.get_state() == DEVICE_STATE_ACTIVATING:
            self.emit('device-activating', dev)
        elif dev.get_state() == DEVICE_STATE_ACTIVATED:
            self.emit('device-activated', dev)

    def get_device(self, dev_op):
        if not self._devices.has_key(dev_op):
            return None
        return self._devices[dev_op]

    def _setup_dbus(self):
        self._sig_handlers = {
            'StateChange': self.state_changed_sig_handler,
            'DeviceAdded': self.device_added_sig_handler,
            'DeviceRemoved': self.device_removed_sig_handler,
            'DeviceActivationStage': self.device_activation_stage_sig_handler,
            'DeviceActivating': self.device_activating_sig_handler,
            'DeviceNowActive': self.device_now_active_sig_handler,
            'DeviceNoLongerActive': self.device_no_longer_active_sig_handler,
            'DeviceActivationFailed': \
                self.device_activation_failed_sig_handler,
            'DeviceCarrierOn': self.device_carrier_on_sig_handler,
            'DeviceCarrierOff': self.device_carrier_off_sig_handler,
            'DeviceStrengthChanged': \
                self.wireless_device_strength_changed_sig_handler,
            'WirelessNetworkAppeared': \
                self.wireless_network_appeared_sig_handler,
            'WirelessNetworkDisappeared': \
                self.wireless_network_disappeared_sig_handler,
            'WirelessNetworkStrengthChanged': \
                self.wireless_network_strength_changed_sig_handler
        }

        try:
            self._nm_proxy = sys_bus.get_object(NM_SERVICE, NM_PATH,
                                                follow_name_owner_changes=True)
            self._nm_obj = dbus.Interface(self._nm_proxy, NM_IFACE)
        except dbus.DBusException, e:
            logging.debug("Could not connect to NetworkManager: %s" % e)
            self._nm_present = False
            return

        sys_bus.add_signal_receiver(self.name_owner_changed_sig_handler,
                                         signal_name="NameOwnerChanged",
                                         dbus_interface="org.freedesktop.DBus")

        for (signal, handler) in self._sig_handlers.items():
            sys_bus.add_signal_receiver(handler, signal_name=signal,
                                        dbus_interface=NM_IFACE)

        # Find out whether or not NMI is running
        try:
            bus_object = sys_bus.get_object('org.freedesktop.DBus',
                                            '/org/freedesktop/DBus')
            name_ = bus_object.GetNameOwner( \
                    "org.freedesktop.NetworkManagerInfo",
                    dbus_interface='org.freedesktop.DBus')
            self._nm_present = True
        except dbus.DBusException:
            self._nm_present = False

    def set_active_device(self, device, network=None,
                          mesh_freq=None, mesh_start=None):
        ssid = ""
        if network:
            ssid = network.get_ssid()
        if device.get_type() == DEVICE_TYPE_802_11_MESH_OLPC:
            if mesh_freq or mesh_start:
                if mesh_freq and not mesh_start:
                    self._nm_obj.setActiveDevice(device.get_op(),
                                                 dbus.Double(mesh_freq))
                elif mesh_start and not mesh_freq:
                    self._nm_obj.setActiveDevice(device.get_op(),
                                                 dbus.Double(0.0),
                                                 dbus.UInt32(mesh_start))
                else:
                    self._nm_obj.setActiveDevice(device.get_op(),
                                                 dbus.Double(mesh_freq),
                                                 dbus.UInt32(mesh_start))
            else:
                self._nm_obj.setActiveDevice(device.get_op())
        else:
            self._nm_obj.setActiveDevice(device.get_op(), ssid)

    def state_changed_sig_handler(self, new_state):
        logging.debug('NM State Changed to %d' % new_state)

    def device_activation_stage_sig_handler(self, device, stage):
        logging.debug('Device Activation Stage "%s" for device %s'
                      % (NM_DEVICE_STAGE_STRINGS[stage], device))
        if not self._devices.has_key(device):
            logging.debug('DeviceActivationStage, device %s does not exist'
                          % (device))
            return
        self._devices[device].set_activation_stage(stage)

    def device_activating_sig_handler(self, device):
        logging.debug('DeviceActivating for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceActivating, device %s does not exist'
                          % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_ACTIVATING)

    def device_now_active_sig_handler(self, device, ssid=None):
        logging.debug('DeviceNowActive for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceNowActive, device %s does not exist'
                          % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_ACTIVATED)

    def device_no_longer_active_sig_handler(self, device):
        logging.debug('DeviceNoLongerActive for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceNoLongerActive, device %s does not exist'
                          % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_INACTIVE)

    def device_activation_failed_sig_handler(self, device, ssid=None):
        logging.debug('DeviceActivationFailed for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceActivationFailed, device %s does not exist'
                          % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_INACTIVE)

    def name_owner_changed_sig_handler(self, name, old, new):
        if name != NM_SERVICE:
            return
        if (old and len(old)) and (not new and not len(new)):
            # NM went away
            self._nm_present = False
            devs = self._devices.keys()
            for op in devs:
                self._remove_device(op)
            self._devices = {}
        elif (not old and not len(old)) and (new and len(new)):
            # NM started up
            self._nm_present = True
            self._get_initial_devices()

    def device_added_sig_handler(self, device):
        logging.debug('DeviceAdded for %s' % (device))
        self._add_device(device)

    def device_removed_sig_handler(self, device):
        logging.debug('DeviceRemoved for %s' % (device))
        self._remove_device(device)

    def wireless_network_appeared_sig_handler(self, device, network):
        if not self._devices.has_key(device):
            return
        self._devices[device].network_appeared(network)

    def wireless_network_disappeared_sig_handler(self, device, network):
        if not self._devices.has_key(device):
            return
        self._devices[device].network_disappeared(network)

    def wireless_device_strength_changed_sig_handler(self, device, strength):
        if not self._devices.has_key(device):
            return
        self._devices[device].set_strength(strength)

    def wireless_network_strength_changed_sig_handler(self, device,
                                                      network, strength):
        if not self._devices.has_key(device):
            return
        net = self._devices[device].get_network(network)
        if net:
            net.set_strength(strength)

    def device_carrier_on_sig_handler(self, device):
        if not self._devices.has_key(device):
            return
        self._devices[device].set_carrier(True)

    def device_carrier_off_sig_handler(self, device):
        if not self._devices.has_key(device):
            return
        self._devices[device].set_carrier(False)

def freq_to_channel(freq):
    ftoc = { 2.412: 1, 2.417: 2, 2.422: 3, 2.427: 4,
	     2.432: 5, 2.437: 6, 2.442: 7, 2.447: 8,
	     2.452: 9, 2.457: 10, 2.462: 11, 2.467: 12,
	     2.472: 13
	     }
    return ftoc[freq]

def channel_to_freq(channel):
    ctof = { 1: 2.412, 2: 2.417, 3: 2.422, 4: 2.427,
	     5: 2.432, 6: 2.437, 7: 2.442, 8: 2.447,
	     9: 2.452, 10: 2.457, 11: 2.462, 12: 2.467,
	     13: 2.472
	     }
    return ctof[channel]

def get_manager():
    return _manager

try:
    _manager = NMClient()
except dbus.DBusException:
    _manager = None
    logging.info('Network manager service not found.')
