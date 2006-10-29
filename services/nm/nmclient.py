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
from sugar.graphics.menu import Menu
from gettext import gettext as _
import os

import nminfo


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
		'init-failed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
		'activated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
		'strength-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
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
		if self._active:
			self.emit('activated')
		self._link = props[15]
		self._caps = props[17]

		if self._type == DEVICE_TYPE_802_11_WIRELESS:
			old_strength = self._strength
			self._strength = props[14]
			if self._strength != old_strength:
				self.emit('strength-changed', self._strength)
			self._update_networks(props[20], props[19])

		self._valid = True

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

	def network_disappeared(self, network):
		if not self._networks.has_key(network):
			return
		if network == self._active_net:
			self._active_net = None
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

class ActivityMenu(Menu):
	def __init__(self, activity_host):
		Menu.__init__(self, activity_host.get_title())

		if not activity_host.get_shared():
			self._add_mesh_action()

		self._add_close_action()

	def _add_mesh_action(self):
		icon = CanvasIcon(icon_name='stock-share-mesh')
		self.add_action(icon, ActivityMenu.ACTION_SHARE) 

	def _add_close_action(self):
		icon = CanvasIcon(icon_name='stock-close')
		self.add_action(icon, ActivityMenu.ACTION_CLOSE) 


NM_STATE_UNKNOWN = 0
NM_STATE_ASLEEP = 1
NM_STATE_CONNECTING = 2
NM_STATE_CONNECTED = 3
NM_STATE_DISCONNECTED = 4

ICON_WIRED = "stock-net-wired"
ICON_WIRELESS_00 = "stock-net-wireless-00"
ICON_WIRELESS_01_20 = "stock-net-wireless-01-20"
ICON_WIRELESS_21_40 = "stock-net-wireless-21-40"
ICON_WIRELESS_41_60 = "stock-net-wireless-41-60"
ICON_WIRELESS_61_80 = "stock-net-wireless-61-80"
ICON_WIRELESS_81_100 = "stock-net-wireless-81-100"

class NMClientApp:
	def __init__(self):
		self.menu = None
		self.nminfo = None
		self._nm_present = False
		self._nm_state = NM_STATE_UNKNOWN
		self._icon_theme = gtk.icon_theme_get_default()
		self._update_timer = 0
		self._active_device = None
		self._devices = {}

		self._icons = {}
		self._cur_icon = None

		try:
			self.nminfo = nminfo.NMInfo()
		except RuntimeError:
			pass
		self._setup_dbus()
		if self._nm_present:
			self._get_nm_state()
			self._get_initial_devices()

		try:
			self._icons = self._load_icons()
		except RuntimeError:
			logging.debug("Couldn't find required icon resources, will exit.")
			os._exit(1)
		self._setup_trayicon()

	def _get_one_icon_pixbuf(self, name):
		info = self._icon_theme.lookup_icon(name, 25, 0)
		if not info or not info.get_filename():
			raise RuntimeError
		return gtk.gdk.pixbuf_new_from_file_at_size(info.get_filename(), 25, 25)

	def _load_icons(self):
		icons = {}
		icons[ICON_WIRED] = self._get_one_icon_pixbuf(ICON_WIRED)
		icons[ICON_WIRELESS_00] = self._get_one_icon_pixbuf(ICON_WIRELESS_00)
		icons[ICON_WIRELESS_01_20] = self._get_one_icon_pixbuf(ICON_WIRELESS_01_20)
		icons[ICON_WIRELESS_21_40] = self._get_one_icon_pixbuf(ICON_WIRELESS_21_40)
		icons[ICON_WIRELESS_41_60] = self._get_one_icon_pixbuf(ICON_WIRELESS_41_60)
		icons[ICON_WIRELESS_61_80] = self._get_one_icon_pixbuf(ICON_WIRELESS_61_80)
		icons[ICON_WIRELESS_81_100] = self._get_one_icon_pixbuf(ICON_WIRELESS_81_100)
		return icons

	def _get_nm_state(self):
		# Grab NM's state
		nm_obj = sys_bus.get_object(NM_SERVICE, NM_PATH)
		nm = dbus.Interface(nm_obj, NM_IFACE)
		nm.state(reply_handler=self._get_state_reply_cb, \
				error_handler=self._get_state_error_cb)

	def _get_state_reply_cb(self, state):
		if self._nm_state != state:
			self._schedule_icon_update(immediate=True)
		self._nm_state = state

	def _get_state_error_cb(self, err):
		logging.debug("Failed to get NetworkManager state! %s" % err)

	def _get_icon(self):
		act_dev = None
		if self._active_device and self._devices.has_key(self._active_device):
			act_dev = self._devices[self._active_device]

		pixbuf = None
		if not self._nm_present \
				or not act_dev \
				or self._nm_state == NM_STATE_UNKNOWN \
				or self._nm_state == NM_STATE_ASLEEP \
				or self._nm_state == NM_STATE_DISCONNECTED:
			pixbuf = self._icons[ICON_WIRELESS_00]
		elif act_dev.get_type() == DEVICE_TYPE_802_3_ETHERNET:
			pixbuf = self._icons[ICON_WIRED]
		elif act_dev.get_type() == DEVICE_TYPE_802_11_WIRELESS:
			strength = act_dev.get_strength()
			if strength <= 0:
				pixbuf = self._icons[ICON_WIRELESS_00]
			elif strength >= 1 and strength <= 20:
				pixbuf = self._icons[ICON_WIRELESS_01_20]
			elif strength >= 21 and strength <= 40:
				pixbuf = self._icons[ICON_WIRELESS_21_40]
			elif strength >= 41 and strength <= 60:
				pixbuf = self._icons[ICON_WIRELESS_41_60]
			elif strength >= 61 and strength <= 80:
				pixbuf = self._icons[ICON_WIRELESS_61_80]
			elif strength >= 81 and strength:
				pixbuf = self._icons[ICON_WIRELESS_81_100]

		if not pixbuf:
			pixbuf = self._icons[ICON_WIRELESS_00]
		return pixbuf

	def _setup_trayicon(self):
		pixbuf = self._get_icon()
		self._trayicon = gtk.status_icon_new_from_pixbuf(pixbuf)
		self._trayicon.connect("popup_menu", self._popup)
		self._trayicon.connect("activate", self._popup)
		self._schedule_icon_update()

	def _popup(self, status, button=0, time=None):
		def menu_pos(menu):
			return gtk.status_icon_position_menu(menu, self._trayicon)

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

	def _update_icon(self):
		pixbuf = self._get_icon()
		if self._cur_icon != pixbuf:
			self._trayicon.set_from_pixbuf(pixbuf)
			self._cur_icon = pixbuf

		blink = False
		if self._nm_state == NM_STATE_CONNECTING:
			blink = True
		self._trayicon.set_blinking(blink)

		self._update_timer = 0
		return False

	def _schedule_icon_update(self, immediate=False):
		if immediate and self._update_timer:
			gobject.source_remove(self._update_timer)
			self._update_timer = 0

		if self._update_timer != 0:
			# There is already an update scheduled
			return

		if immediate:
			self._update_timer = gobject.idle_add(self._update_icon)
		else:
			self._update_timer = gobject.timeout_add(2000, self._update_icon)

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
		nm_obj = sys_bus.get_object(NM_SERVICE, NM_PATH)
		nm = dbus.Interface(nm_obj, NM_IFACE)
		nm.getDevices(reply_handler=self._get_initial_devices_reply_cb, \
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
		self._schedule_icon_update(immediate=True)

	def _dev_activated_cb(self, dev):
		op = dev.get_op()
		if not self._devices.has_key(op):
			return
		if not dev.get_active():
			return
		self._active_device = op
		self._schedule_icon_update(immediate=True)

	def _dev_strength_changed_cb(self, dev, strength):
		op = dev.get_op()
		if not self._devices.has_key(op):
			return
		if not dev.get_active():
			return
		self._schedule_icon_update()

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

		self.nm_proxy = sys_bus.get_object(NM_SERVICE, NM_PATH)

		sys_bus.add_signal_receiver(self.name_owner_changed_sig_handler,
										 signal_name="NameOwnerChanged",
										 dbus_interface="org.freedesktop.DBus")

		sys_bus.add_signal_receiver(self.catchall_signal_handler,
										 dbus_interface=NM_IFACE) 

		sys_bus.add_signal_receiver(self.catchall_signal_handler,
										 dbus_interface=NM_IFACE + 'Devices')

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

	@dbus.decorators.explicitly_pass_message
	def catchall_signal_handler(self, *args, **keywords):
		dbus_message = keywords['dbus_message']
		mem = dbus_message.get_member()
		iface = dbus_message.get_interface()

		if iface == NM_IFACE and mem in self._sig_handlers.keys():
			return

	 	logging.debug('Caught signal %s.%s' % (dbus_message.get_interface(), mem))
		for arg in args:
			logging.debug('        ' + str(arg))

	def device_activation_stage_sig_handler(self, device, stage):
	    print 'Network Manager Device Stage "%s" for device %s'%(NM_DEVICE_STAGE_STRINGS[stage], device)

	def state_change_sig_handler(self, state):
		print "State: %s" % state
		self._nm_state = state
		self._schedule_icon_update(immediate=True)

	def device_activating_sig_handler(self, device):
		print 'Device %s activating'%device

	def device_now_active_sig_handler(self, device, ssid=None):
		if not self._devices.has_key(device):
			return
		self._devices[devices].set_active(True, ssid)
		self._schedule_icon_update(immediate=True)

	def device_no_longer_active_sig_handler(self, device):
		if not self._devices.has_key(device):
			return
		self._devices[devices].set_active(False)
		self._schedule_icon_update(immediate=True)

	def name_owner_changed_sig_handler(self, name, old, new):
		if name != NM_SERVICE:
			return
		if (old and len(old)) and (not new and not len(new)):
			# NM went away
			self._nm_present = False
			self._schedule_update_timer()
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

	def run(self):
		loop = gobject.MainLoop()
		try:
			loop.run()
		except KeyboardInterrupt:
			pass

