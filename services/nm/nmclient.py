# vi: ts=4 ai noet 
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

import dbus
import dbus.glib
import dbus.decorators
import gobject
import gtk
import logging
from gettext import gettext as _

import nminfo

NM_STATE_STRINGS=("Unknown",
	"Asleep",
	"Connecting",
	"Connected",
	"Disconnected"
)

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


class Network(gobject.GObject):
	__gsignals__ = {
		'init-failed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
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

	def is_valid(self):
		return self._valid

	def add_to_menu(self, menu):
		item = gtk.CheckMenuItem()
		strength = self._strength
		if strength > 100:
			strength = 100
		elif strength < 0:
			strength = 0
		label_str = "%s (%d%%)" % (self._ssid, strength)
		label = gtk.Label(label_str)
		label.set_alignment(0.0, 0.5)
		item.add(label)
		item.show_all()
		menu.add(item)


class Device(gobject.GObject):
	__gsignals__ = {
		'init-failed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
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
			self._strength = props[14]
			self._update_networks(props[20], props[19])

		self._valid = True

	def _update_networks(self, net_ops, active_op):
		for op in net_ops:
			net = Network(op)
			self._networks[op] = net
			net.connect('init-failed', self._net_init_failed)
			if op == active_op:
				self._active_net = net

	def _update_error_cb(self, err):
		logging.debug("Device(%s): failed to update. (%s)" % (self._op, err))
		self._valid = False
		self.emit('init-failed')

	def _net_init_failed(self, net):
		net_op = net.get_op()
		if not self._networks.has_key(net_op):
			return
		net = self._networks[net_op]
		if net == self._active_net:
			self._active_net = None
		del self._networks[net_op]

	def _add_to_menu_wired(self, menu):
		item = gtk.CheckMenuItem()
		label = gtk.Label(_("Wired Network"))
		label.set_alignment(0.0, 0.5);
		item.add(label)
		if self._caps & NM_DEVICE_CAP_CARRIER_DETECT:
			item.set_sensitive(self._link)
		item.show_all()
		menu.add(item)

	def _add_to_menu_wireless(self, menu):
		for net in self._networks.values():
			if not net.is_valid():
				continue
			net.add_to_menu(menu)

	def add_to_menu(self, menu):
		if self._type == DEVICE_TYPE_802_3_ETHERNET:
			self._add_to_menu_wired(menu)
		elif self._type == DEVICE_TYPE_802_11_WIRELESS:
			self._add_to_menu_wireless(menu)

	def get_op(self):
		return self._op

	def get_network(self, op):
		if self._networks.has_key(op):
			return self._networks[op]
		return None

	def get_network_ops(self):
		return self._networks.keys()

	def get_strength(self):
		return self._strength

	def set_strength(self, strength):
		if strength >= 0 and strength <= 100:
			self._strength = strength
		else:
			self._strength = 0

	def network_appeared(self, network):
		if self._networks.has_key(network):
			return
		net = Network(network)
		self._networks[network] = net
		net.connect('init-failed', self._net_init_failed)

	def network_disappeared(self, network):
		if not self._networks.has_key(network):
			return
		del self._networks[network]

	def get_type(self):
		return self._type

	def is_valid(self):
		return self._valid

	def set_carrier(self, on):
		self._link = on

class NMClientApp:
	def __init__(self):
		self.menu = None
		self.nminfo = None
		try:
			self.nminfo = nminfo.NMInfo()
		except RuntimeError:
			pass
		self._setup_dbus()

		self._devices = {}
		self._update_devices()

		self._setup_trayicon()

	def _setup_trayicon(self):
		self.trayicon = gtk.status_icon_new_from_file("/home/dcbw/Development/olpc/nm-python-client/icons/nm-no-connection.png")
		self.trayicon.connect("popup_menu", self._popup)
		self.trayicon.connect("activate", self._popup)

	def _popup(self, status, button=0, time=None):
		def menu_pos(menu):
			return gtk.status_icon_position_menu(menu, self.trayicon)

		if time is None:
			time = gtk.get_current_event_time()
		if self.menu:
			del self.menu
		self.menu = self._construct_new_menu()
		self.menu.popup(None, None, menu_pos, button, time)
		self.menu.show_all()

	def _construct_new_menu(self):
		menu = gtk.Menu()

		# Wired devices first
		for dev in self._devices.values():
			if not dev.is_valid():
				continue
			if dev.get_type() != DEVICE_TYPE_802_3_ETHERNET:
				continue
			dev.add_to_menu(menu)

		# Wireless devices second
		for dev in self._devices.values():
			if not dev.is_valid():
				continue
			if dev.get_type() != DEVICE_TYPE_802_11_WIRELESS:
				continue
			dev.add_to_menu(menu)

		return menu

	def _update_devices_reply_cb(self, ops):
		for op in ops:
			dev = Device(op)
			self._devices[op] = dev
			dev.connect('init-failed', self._dev_init_failed_cb)

	def _dev_init_failed_cb(self, dev):
		# Device failed to initialize, likely due to dbus errors or something
		op = dev.get_op()
		if self._devices.has_key(op):
			del self._devices[op]

	def _update_devices_error_cb(self, err):
		logging.debug("Error updating devices (%s)" % err)

	def _update_devices(self):
		for dev_name in self._devices.keys():
			del self._devices[dev_name]
		self._devices = {}

		nm_obj = sys_bus.get_object(NM_SERVICE, NM_PATH)
		nm = dbus.Interface(nm_obj, NM_IFACE)
		nm.getDevices(reply_handler=self._update_devices_reply_cb, \
				error_handler=self._update_devices_error_cb)

	def _setup_dbus(self):
		sig_handlers = {
			'DeviceActivationStage': self.device_activation_stage_sig_handler,
			'StateChange': self.state_change_sig_handler,
			'DeviceActivating': self.device_activating_sig_handler,
			'DeviceNowActive': self.device_now_active_sig_handler,
			'WirelessNetworkAppeared': self.wireless_network_appeared_sig_handler,
			'WirelessNetworkDisappeared': self.wireless_network_disappeared_sig_handler,
			'DeviceStrengthChanged': self.wireless_device_strength_changed_sig_handler,
			'WirelessNetworkStrengthChanged': self.wireless_network_strength_changed_sig_handler,
			'DeviceCarrierOn': self.device_carrier_on_sig_handler,
			'DeviceCarrierOff': self.device_carrier_off_sig_handler
		}

		self.nm_proxy = sys_bus.get_object(NM_SERVICE, NM_PATH)

		sys_bus.add_signal_receiver(self.name_owner_changed_sig_handler,
										 signal_name="NameOwnerChanged",
										 dbus_interface="org.freedesktop.DBus")

		sys_bus.add_signal_receiver(self.catchall_signal_handler,
										 dbus_interface=NM_IFACE) 

		sys_bus.add_signal_receiver(self.catchall_signal_handler,
										 dbus_interface=NM_IFACE + 'Devices')

		for (signal, handler) in sig_handlers.items():
			sys_bus.add_signal_receiver(handler, signal_name=signal, dbus_interface=NM_IFACE)

	@dbus.decorators.explicitly_pass_message
	def catchall_signal_handler(*args, **keywords):
		dbus_message = keywords['dbus_message']
		mem = dbus_message.get_member()
		iface = dbus_message.get_interface()

		if iface == NM_IFACE and \
		   (mem == 'DeviceActivationStage' or \
		    mem == 'StateChange' or \
		    mem == 'DeviceActivating' or \
		    mem == 'DeviceNowActive' or \
		    mem == 'DeviceStrengthChanged' or \
		    mem == 'WirelessNetworkAppeared' or \
		    mem == 'WirelessNetworkDisappeared' or \
		    mem == 'WirelessNetworkStrengthChanged'):
			return

	 	logging.debug('Caught signal %s.%s' % (dbus_message.get_interface(), mem))
		for arg in args:
			logging.debug('        ' + str(arg))

	def device_activation_stage_sig_handler(self, device, stage):
	    print 'Network Manager Device Stage "%s" for device %s'%(NM_DEVICE_STAGE_STRINGS[stage], device)

	def state_change_sig_handler(self, state):
		print 'Network Manager State "%s"'%NM_STATE_STRINGS[state]

	def device_activating_sig_handler(self, device):
		print 'Device %s activating'%device

	def device_now_active_sig_handler(self, device, essid=None):
		print 'Device %s now activated (%s)'%(device, essid)

	def name_owner_changed_sig_handler(self, name, old, new):
		if name != NM_SERVICE:
			return
		if (old and len(old)) and (not new and not len(new)):
			# NM went away
			pass
		elif (not old and not len(old)) and (new and len(new)):
			# NM started up
			self._update_devices()

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

	def run(self):
		loop = gobject.MainLoop()
		try:
			loop.run()
		except KeyboardInterrupt:
			pass

