#
# Copyright (C) 2006-2007 Red Hat, Inc.
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
import dbus.glib
import dbus.decorators
import gobject
import gtk

from hardware import nminfo

IW_AUTH_ALG_OPEN_SYSTEM = 0x00000001
IW_AUTH_ALG_SHARED_KEY  = 0x00000002

NM_DEVICE_STAGE_STRINGS=("Unknown",
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

sys_bus = dbus.SystemBus()

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

class Network(gobject.GObject):
    __gsignals__ = {
        'initialized'     : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([gobject.TYPE_BOOLEAN])),
        'strength-changed': (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([])),
        'state-changed'   : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([]))
    }

    def __init__(self, op):
        gobject.GObject.__init__(self)
        self._op = op
        self._ssid = None
        self._mode = None
        self._strength = 0
        self._caps = 0
        self._valid = False
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
        if self._caps & NM_802_11_CAP_PROTO_WPA or self._caps & NM_802_11_CAP_PROTO_WPA2:
            if not (self._caps & NM_802_11_CAP_KEY_MGMT_PSK):
                # 802.1x is not supported at this time
                logging.debug("Net(%s): ssid '%s' dropping because 802.1x is unsupported" % (self._op,
                        self._ssid))
                self._valid = False
                self.emit('initialized', self._valid)
                return
        if self._mode != IW_MODE_INFRA:
            # Don't show Ad-Hoc networks; they usually don't DHCP and therefore
            # won't work well here.  This also works around the bug where we show
            # our own mesh SSID on the Mesh view when in mesh mode
            logging.debug("Net(%s): ssid '%s' is adhoc; not showing" % (self._op,
                    self._ssid))
            self._valid = False
            self.emit('initialized', self._valid)
            return

        self._valid = True
        logging.debug("Net(%s): caps 0x%X" % (self._ssid, self._caps))
        self.emit('initialized', self._valid)

    def _update_error_cb(self, err):
        logging.debug("Net(%s): failed to update. (%s)" % (self._op, err))
        self._valid = False
        self.emit('initialized', self._valid)

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

class Device(gobject.GObject):
    __gsignals__ = {
        'initialized':         (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'init-failed':         (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'ssid-changed':        (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'strength-changed':    (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'state-changed':       (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'network-appeared':    (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT])),
        'network-disappeared': (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, op):
        gobject.GObject.__init__(self)
        self._op = op
        self._iface = None
        self._type = DEVICE_TYPE_UNKNOWN
        self._udi = None
        self._active = False
        self._act_stage = 0
        self._strength = 0
        self._link = False
        self._valid = False
        self._networks = {}
        self._caps = 0
        self._state = DEVICE_STATE_INACTIVE
        self._active_network = None

        obj = sys_bus.get_object(NM_SERVICE, self._op)
        dev = dbus.Interface(obj, NM_IFACE_DEVICES)
        dev.getProperties(reply_handler=self._update_reply_cb,
                error_handler=self._update_error_cb)

    def _is_activating(self):
        if self._active and self._act_stage >= 1 and self._act_stage <= 7:
            return True
        return False

    def _is_activated(self):
        if self._active and self._act_stage == 8:
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
            net = Network(op)
            self._networks[op] = net
            net.connect('initialized', lambda *args: self._net_initialized_cb(active_op, *args))

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
        if self._networks.has_key(network):
            return
        net = Network(network)
        self._networks[network] = net
        net.connect('initialized', lambda *args: self._net_initialized_cb(None, *args))

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

        self._active_network = network

        # don't emit ssid-changed for networks that are not yet valid
        if self._valid:
            if self._active_network and self._active_network.is_valid():
                self.emit('ssid-changed')
            elif not self._active_network:
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

        self._state = state
        if self._valid:
            self.emit('state-changed')

        if self._type == DEVICE_TYPE_802_11_WIRELESS:
            if state == DEVICE_STATE_INACTIVE:
                self.set_active_network(None)
            else:
                obj = sys_bus.get_object(NM_SERVICE, self._op)
                dev = dbus.Interface(obj, NM_IFACE_DEVICES)
                dev.getActiveNetwork(reply_handler=lambda *args: self._get_active_net_cb(state, *args),
                            error_handler=self._get_active_net_error_cb)

    def get_ssid(self):
        if self._active_network and self._active_network.is_valid():
            return self._active_network.get_ssid()
        elif not self._active_network:
            return None

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
        self._update_timer = 0
        self._devices = {}

        try:
            self.nminfo = nminfo.NMInfo(self)
        except RuntimeError:
            pass
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
        self._nm_obj.getDevices(reply_handler=self._get_initial_devices_reply_cb, \
                error_handler=self._get_initial_devices_error_cb)

    def _add_device(self, dev_op):
        if self._devices.has_key(dev_op):
            return
        dev = Device(dev_op)
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
            'DeviceActivationFailed': self.device_activation_failed_sig_handler,
            'DeviceCarrierOn': self.device_carrier_on_sig_handler,
            'DeviceCarrierOff': self.device_carrier_off_sig_handler,
            'DeviceStrengthChanged': self.wireless_device_strength_changed_sig_handler,
            'WirelessNetworkAppeared': self.wireless_network_appeared_sig_handler,
            'WirelessNetworkDisappeared': self.wireless_network_disappeared_sig_handler,
            'WirelessNetworkStrengthChanged': self.wireless_network_strength_changed_sig_handler
        }

        try:
            self._nm_proxy = sys_bus.get_object(NM_SERVICE, NM_PATH)
            self._nm_obj = dbus.Interface(self._nm_proxy, NM_IFACE)
        except dbus.DBusException, e:
            logging.debug("Could not connect to NetworkManager!")
            self._nm_present = False
            return

        sys_bus.add_signal_receiver(self.name_owner_changed_sig_handler,
                                         signal_name="NameOwnerChanged",
                                         dbus_interface="org.freedesktop.DBus")

        for (signal, handler) in self._sig_handlers.items():
            sys_bus.add_signal_receiver(handler, signal_name=signal, dbus_interface=NM_IFACE)

        # Find out whether or not NMI is running
        try:
            bus_object = sys_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            name = bus_object.GetNameOwner("org.freedesktop.NetworkManagerInfo", \
                    dbus_interface='org.freedesktop.DBus')
            if name:
                self._nm_present = True
        except dbus.DBusException:
            pass

    def set_active_device(self, device, network=None):
        ssid = ""
        if network:
            ssid = network.get_ssid()
        try:
            # NM 0.6.4 and earlier have a bug which returns an
            # InvalidArguments error if no security information is passed
            # for wireless networks
            self._nm_obj.setActiveDevice(device.get_op(), ssid)
        except dbus.DBusException, e:
            if str(e).find("invalid arguments"):
                pass
            else:
                raise dbus.DBusException(e)

    def state_changed_sig_handler(self, new_state):
        logging.debug('NM State Changed to %d' % new_state)

    def device_activation_stage_sig_handler(self, device, stage):
        logging.debug('Device Activation Stage "%s" for device %s' % (NM_DEVICE_STAGE_STRINGS[stage], device))

    def device_activating_sig_handler(self, device):
        logging.debug('DeviceActivating for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceActivating, device %s does not exist' % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_ACTIVATING)

    def device_now_active_sig_handler(self, device, ssid=None):
        logging.debug('DeviceNowActive for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceNowActive, device %s does not exist' % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_ACTIVATED)

    def device_no_longer_active_sig_handler(self, device):
        logging.debug('DeviceNoLongerActive for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceNoLongerActive, device %s does not exist' % (device))
            return
        self._devices[device].set_state(DEVICE_STATE_INACTIVE)

    def device_activation_failed_sig_handler(self, device, ssid=None):
        logging.debug('DeviceActivationFailed for %s' % (device))
        if not self._devices.has_key(device):
            logging.debug('DeviceActivationFailed, device %s does not exist' % (device))
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

    def wireless_network_strength_changed_sig_handler(self, device, network, strength):
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
