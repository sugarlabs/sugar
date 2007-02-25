#
# Copyright (C) 2006, Red Hat, Inc.
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

from hardware.wepkeydialog import WEPKeyDialog
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
    "Cancled"
)

NM_SERVICE = 'org.freedesktop.NetworkManager'
NM_IFACE = 'org.freedesktop.NetworkManager'
NM_IFACE_DEVICES = 'org.freedesktop.NetworkManager.Devices'
NM_PATH = '/org/freedesktop/NetworkManager'

DEVICE_TYPE_UNKNOWN = 0
DEVICE_TYPE_802_3_ETHERNET = 1
DEVICE_TYPE_802_11_WIRELESS = 2

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

class Network(gobject.GObject):
    __gsignals__ = {
        'init-failed'     : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([])),
        'strength-changed': (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE, ([]))
    }

    def __init__(self, op):
        gobject.GObject.__init__(self)
        self._op = op
        self._ssid = None
        self._mode = None
        self._strength = 0
        self._valid = False

        obj = sys_bus.get_object(NM_SERVICE, self._op)
        net = dbus.Interface(obj, NM_IFACE_DEVICES)
        net.getProperties(reply_handler=self._update_reply_cb,
                error_handler=self._update_error_cb)

    def _update_reply_cb(self, *props):
        self._ssid = props[1]
        self._strength = props[3]
        self._mode = props[6]
        caps = props[7]
        if caps & NM_802_11_CAP_PROTO_WPA or caps & NM_802_11_CAP_PROTO_WPA2:
            # We do not support WPA at this time, so don't show
            # WPA-enabled access points in the menu
            logging.debug("Net(%s): ssid '%s' dropping because WPA[2] unsupported" % (self._op,
                    self._ssid))
            self._valid = False
            self.emit('init-failed')
        else:
            self._valid = True
            logging.debug("Net(%s): ssid '%s', mode %d, strength %d" % (self._op,
                    self._ssid, self._mode, self._strength))

    def _update_error_cb(self, err):
        logging.debug("Net(%s): failed to update. (%s)" % (self._op, err))
        self._valid = False
        self.emit('init-failed')

    def get_ssid(self):
        return self._ssid

    def get_op(self):
        return self._op

    def get_strength(self):
        return self._strength

    def set_strength(self, strength):
        self._strength = strength
        self.emit('strength-changed')

    def is_valid(self):
        return self._valid

class Device(gobject.GObject):
    __gsignals__ = {
        'init-failed':         (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'activated':           (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'deactivated':         (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE, ([])),
        'strength-changed':    (gobject.SIGNAL_RUN_FIRST,
                                gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT])),
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
        self._strength = 0
        self._link = False
        self._valid = False
        self._networks = {}
        self._active_net = None
        self._caps = 0

        obj = sys_bus.get_object(NM_SERVICE, self._op)
        dev = dbus.Interface(obj, NM_IFACE_DEVICES)
        dev.getProperties(reply_handler=self._update_reply_cb,
                error_handler=self._update_error_cb)

    def _update_reply_cb(self, *props):
        self._iface = props[1]
        self._type = props[2]
        self._udi = props[3]
        self._active = props[4]
        self._link = props[15]
        self._caps = props[17]

        if self._type == DEVICE_TYPE_802_11_WIRELESS:
            old_strength = self._strength
            self._strength = props[14]
            if self._strength != old_strength:
                self.emit('strength-changed', self._strength)
            self._update_networks(props[20], props[19])

        self._valid = True

        if self._active:
            self.emit('activated')
        else:
            self.emit('deactivated')

    def _update_networks(self, net_ops, active_op):
        for op in net_ops:
            net = Network(op)
            self._networks[op] = net
            net.connect('init-failed', self._net_init_failed)
            if op == active_op:
                self._active_net = op

    def _update_error_cb(self, err):
        logging.debug("Device(%s): failed to update. (%s)" % (self._op, err))
        self._valid = False
        self.emit('init-failed')

    def _net_init_failed(self, net):
        net_op = net.get_op()
        if not self._networks.has_key(net_op):
            return
        if net_op == self._active_net:
            self._active_net = None
        del self._networks[net_op]

    def get_op(self):
        return self._op

    def get_networks(self):
        return self._networks.values()

    def get_network(self, op):
        if self._networks.has_key(op):
            return self._networks[op]
        return None

    def get_network_ops(self):
        return self._networks.keys()

    def get_strength(self):
        return self._strength

    def set_strength(self, strength):
        if strength == self._strength:
            return False

        if strength >= 0 and strength <= 100:
            self._strength = strength
        else:
            self._strength = 0

        self.emit('strength-changed', self._strength)

    def network_appeared(self, network):
        if self._networks.has_key(network):
            return
        net = Network(network)
        self._networks[network] = net
        net.connect('init-failed', self._net_init_failed)
        self.emit('network-appeared', net)

    def network_disappeared(self, network):
        if not self._networks.has_key(network):
            return
        if network == self._active_net:
            self._active_net = None

        self.emit('network-disappeared', self._networks[network])

        del self._networks[network]

    def get_active(self):
        return self._active

    def set_active(self, active, ssid=None):
        self._active = active
        if self._type == DEVICE_TYPE_802_11_WIRELESS:
            if not ssid:
                self._active_net = None
            else:
                for (op, net) in self._networks.items():
                    if net.get_ssid() == ssid:
                        self._active_net = op

    def get_type(self):
        return self._type

    def is_valid(self):
        return self._valid

    def set_carrier(self, on):
        self._link = on

    def get_capabilities(self):
        return self._caps

NM_STATE_UNKNOWN = 0
NM_STATE_ASLEEP = 1
NM_STATE_CONNECTING = 2
NM_STATE_CONNECTED = 3
NM_STATE_DISCONNECTED = 4

class NMClient(gobject.GObject):
    __gsignals__ = {
        'device-activated' : (gobject.SIGNAL_RUN_FIRST,
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
        self._nm_state = NM_STATE_UNKNOWN
        self._update_timer = 0
        self._active_device = None
        self._devices = {}

        try:
            self.nminfo = nminfo.NMInfo(self)
        except RuntimeError:
            pass
        self._setup_dbus()
        if self._nm_present:
            self._get_nm_state()
            self._get_initial_devices()

    def get_devices(self):
        return self._devices

    def _get_nm_state(self):
        # Grab NM's state
        self._nm_obj.state(reply_handler=self._get_state_reply_cb, \
                error_handler=self._get_state_error_cb)

    def _get_state_reply_cb(self, state):
        self._nm_state = state

    def _get_state_error_cb(self, err):
        logging.debug("Failed to get NetworkManager state! %s" % err)

    def _get_initial_devices_reply_cb(self, ops):
        for op in ops:
            self._add_device(op)

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
        dev.connect('activated', self._dev_activated_cb)
        dev.connect('strength-changed', self._dev_strength_changed_cb)

    def _remove_device(self, dev_op):
        if not self._devices.has_key(dev_op):
            return
        if self._active_device == dev_op:
            self._active_device = None
        dev = self._devices[dev_op]
        dev.disconnect('activated')
        dev.disconnect('init-failed')
        dev.disconnect('strength-changed')
        del self._devices[dev_op]

        self.emit('device-removed', dev)

    def _dev_activated_cb(self, dev):
        op = dev.get_op()
        if not self._devices.has_key(op):
            return
        if not dev.get_active():
            return
        self._active_device = op

        self.emit('device-activated', dev)

    def _dev_strength_changed_cb(self, dev, strength):
        op = dev.get_op()
        if not self._devices.has_key(op):
            return
        if not dev.get_active():
            return

    def get_device(self, dev_op):
        if not self._devices.has_key(dev_op):
            return None
        return self._devices[dev_op]

    def _setup_dbus(self):
        self._sig_handlers = {
            'StateChange': self.state_change_sig_handler,
            'DeviceAdded': self.device_added_sig_handler,
            'DeviceRemoved': self.device_removed_sig_handler,
            'DeviceActivationStage': self.device_activation_stage_sig_handler,
            'DeviceActivating': self.device_activating_sig_handler,
            'DeviceNowActive': self.device_now_active_sig_handler,
            'DeviceNoLongerActive': self.device_no_longer_active_sig_handler,
            'DeviceCarrierOn': self.device_carrier_on_sig_handler,
            'DeviceCarrierOff': self.device_carrier_off_sig_handler,
            'DeviceStrengthChanged': self.wireless_device_strength_changed_sig_handler,
            'WirelessNetworkAppeared': self.wireless_network_appeared_sig_handler,
            'WirelessNetworkDisappeared': self.wireless_network_disappeared_sig_handler,
            'WirelessNetworkStrengthChanged': self.wireless_network_strength_changed_sig_handler
        }

        self._nm_proxy = sys_bus.get_object(NM_SERVICE, NM_PATH)
        self._nm_obj = dbus.Interface(self._nm_proxy, NM_IFACE)

        sys_bus.add_signal_receiver(self.name_owner_changed_sig_handler,
                                         signal_name="NameOwnerChanged",
                                         dbus_interface="org.freedesktop.DBus")

        for (signal, handler) in self._sig_handlers.items():
            sys_bus.add_signal_receiver(handler, signal_name=signal, dbus_interface=NM_IFACE)

        # Find out whether or not NM is running
        try:
            bus_object = sys_bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
            name = bus_object.GetNameOwner("org.freedesktop.NetworkManagerInfo", \
                    dbus_interface='org.freedesktop.DBus')
            if name:
                self._nm_present = True
        except dbus.DBusException:
            pass

    def set_active_device(self, device, network):
        net_op = ""
        if network:
            net_op = network.get_op()
        try:
            # NM 0.6.4 and earlier have a bug which returns an
            # InvalidArguments error if no security information is passed
            # for wireless networks
            self._nm_obj.setActiveDevice(device.get_op(), network.get_ssid())
        except dbus.DBusException, e:
            if str(e).find("invalid arguments"):
                pass
            else:
                raise dbus.DBusException(e)

    def get_key_for_network(self, net, async_cb, async_err_cb):
        # Throw up a dialog asking for the key here, and set
        # the authentication algorithm to the given one, if any
        #
        # Key needs to be limited to _either_ 10 or 26 digits long,
        # and contain _only_ _hex_ digits, 0-9 or a-f
        #
        # Auth algorithm should be a dropdown of: [Open System, Shared Key],
        # mapping to the values [IW_AUTH_ALG_OPEN_SYSTEM, IW_AUTH_ALG_SHARED_KEY]
        # above

        self._key_dialog = WEPKeyDialog(net, async_cb, async_err_cb)
        self._key_dialog.connect("response", self._key_dialog_response_cb)
        self._key_dialog.connect("destroy", self._key_dialog_destroy_cb)
        self._key_dialog.show_all()

    def _key_dialog_destroy_cb(self, widget, foo=None):
        if widget != self._key_dialog:
            return
        self._key_dialog_response_cb(widget, gtk.RESPONSE_CANCEL)

    def _key_dialog_response_cb(self, widget, response_id):
        if widget != self._key_dialog:
            return
        key = self._key_dialog.get_key()
        wep_auth_alg = self._key_dialog.get_auth_alg()
        net = self._key_dialog.get_network()
        (async_cb, async_err_cb) = self._key_dialog.get_callbacks()

        # Clear self._key_dialog before we call destroy(), otherwise
        # the destroy will trigger and we'll get called again by
        # self._key_dialog_destroy_cb
        self._key_dialog = None
        widget.destroy()

        if response_id == gtk.RESPONSE_OK:
            self.nminfo.get_key_for_network_cb(
                    net, key, wep_auth_alg, async_cb, async_err_cb, canceled=False)
        else:
            self.nminfo.get_key_for_network_cb(
                    net, None, None, async_cb, async_err_cb, canceled=True)

    def cancel_get_key_for_network(self):
        # Close the wireless key dialog and just have it return
        # with the 'canceled' argument set to true
        if not self._key_dialog:
            return
        self._key_dialog_destroy_cb(self._key_dialog)

    def device_activation_stage_sig_handler(self, device, stage):
        logging.debug('Device Activation Stage "%s" for device %s' % (NM_DEVICE_STAGE_STRINGS[stage], device))

    def state_change_sig_handler(self, state):
        self._nm_state = state

    def device_activating_sig_handler(self, device):
        self._active_device = device

    def device_now_active_sig_handler(self, device, ssid=None):
        if not self._devices.has_key(device):
            return
        self._active_device = device
        self._devices[device].set_active(True, ssid)

    def device_no_longer_active_sig_handler(self, device):
        if not self._devices.has_key(device):
            return
        if self._active_device == device:
            self._active_device = None
        self._devices[device].set_active(False)

    def name_owner_changed_sig_handler(self, name, old, new):
        if name != NM_SERVICE:
            return
        if (old and len(old)) and (not new and not len(new)):
            # NM went away
            self._nm_present = False
            for op in self._devices.keys():
                del self._devices[op]
            self._devices = {}
            self._active_device = None
            self._nm_state = NM_STATE_UNKNOWN
        elif (not old and not len(old)) and (new and len(new)):
            # NM started up
            self._nm_present = True
            self._get_nm_state()
            self._get_initial_devices()

    def device_added_sig_handler(self, device):
        self._add_device(device)

    def device_removed_sig_handler(self, device):
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
