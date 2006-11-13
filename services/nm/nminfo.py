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
import dbus.service
import time
import os
import binascii
from ConfigParser import ConfigParser
import logging

import nmclient
try:
	from sugar import env
except ImportError:
	pass

NM_INFO_IFACE='org.freedesktop.NetworkManagerInfo'
NM_INFO_PATH='/org/freedesktop/NetworkManagerInfo'


class NoNetworks(dbus.DBusException):
	def __init__(self):
		dbus.DBusException.__init__(self)
		self._dbus_error_name = NM_INFO_IFACE + '.NoNetworks'

class CanceledKeyRequestError(dbus.DBusException):
	def __init__(self):
		dbus.DBusException.__init__(self)
		self._dbus_error_name = NM_INFO_IFACE + '.CanceledError'


class NetworkInvalidError(Exception):
	pass


class NMConfig(ConfigParser):
	def get_bool(self, section, name):
		opt = self.get(section, name)
		if type(opt) == type(""):
			if opt.lower() == 'yes' or opt.lower() == 'true':
				return True
			elif opt.lower() == 'no' or opt.lower() == 'false':
				return False
		raise ValueError("Invalid format for %s/%s.  Should be one of [yes, no, true, false]." % (section, name))

	def get_list(self, section, name):
		opt = self.get(section, name)
		if type(opt) == type(""):
			if not len(opt):
				return []
			try:
				return opt.split()
			except Exception:
				pass
		raise ValueError("Invalid format for %s/%s.  Should be a space-separate list." % (section, name))

	def get_int(self, section, name):
		opt = self.get(section, name)
		try:
			return int(opt)
		except Exception:
			pass
		raise ValueError("Invalid format for %s/%s.  Should be a valid integer." % (section, name))


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


class Security(object):
	def __init__(self, we_cipher):
		self._we_cipher = we_cipher

	def read_from_config(self, cfg, name):
		pass

	def read_from_args(self, args):
		pass

	def new_from_config(cfg, name):
		security = None
		try:
			we_cipher = cfg.get_int(name, "we_cipher")
			if we_cipher == IW_AUTH_CIPHER_NONE:
				security = Security(we_cipher)
			elif we_cipher == IW_AUTH_CIPHER_WEP40 or we_cipher == IW_AUTH_CIPHER_WEP104:
				security = WEPSecurity(we_cipher)
			else:
				# FIXME: find a way to make WPA config option matrix not
				# make you want to throw up
				raise ValueError("Unsupported security combo")
			security.read_from_config(cfg, name)
		except (NoOptionError, ValueError), e:
			return None
		return security
	new_from_config = staticmethod(new_from_config)

	def new_from_args(we_cipher, key, auth_alg):
		security = None
		try:
			if we_cipher == IW_AUTH_CIPHER_NONE:
				security = Security(we_cipher)
			elif we_cipher == IW_AUTH_CIPHER_WEP40 or we_cipher == IW_AUTH_CIPHER_WEP104:
				security = WEPSecurity(we_cipher)
			else:
				# FIXME: find a way to make WPA config option matrix not
				# make you want to throw up
				raise ValueError("Unsupported security combo")
			security.read_from_args(key, auth_alg)
		except (NoOptionError, ValueError), e:
			del security
			return None
		return security
	new_from_args = staticmethod(new_from_args)

	def get_properties(self):
		return [dbus.Int32(self._we_cipher)]

	def write_to_config(self, section, config):
		config.set(section, "we_cipher", self._we_cipher)


class WEPSecurity(Security):
	def read_from_args(self, key, auth_alg):
#		if len(args) != 2:
#			raise ValueError("not enough arguments")
#		if not isinstance(args[0], str):
#			raise ValueError("wrong argument type for key")
#		if not isinstance(args[1], int):
#			raise ValueError("wrong argument type for auth_alg")
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
			a = binascii.a2b_hex(self._key)
		except TypeError:
			raise ValueError("Key was not a hexadecimal string.")
			
		self._auth_alg = cfg.get_int(name, "auth_alg")
		if self._auth_alg != IW_AUTH_ALG_OPEN_SYSTEM and self._auth_alg != IW_AUTH_ALG_SHARED_KEY:
			raise ValueError("Invalid authentication algorithm %d" % self._auth_alg)

	def get_properties(self):
		args = Security.get_properties(self)
		args.append(self._key)
		args.append(dbus.Int32(self._auth_alg))
		return args

	def write_to_config(self, section, config):
		Security.write_to_config(self, section, config)
		config.set(section, "key", self._key)
		config.set(section, "auth_alg", self._auth_alg)


class Network:
	def __init__(ssid):
		self.ssid = ssid
		self.timestamp = time.now()
		self.fallback = False
		self.bssids = []
		self.we_cipher = 0
		self._security = None

	def get_properties(self):
		args = [network.ssid, network.timestamp, network.fallback, network.bssids]
		args += self._security.get_properties()
		return tuple(args)

	def get_security(self):
		return self._security.get_properties()

	def set_security(self, security):
		self._security = security

	def read_from_args(self, auto, fallback, bssid, we_cipher, *args):
		if auto == False:
			self.timestamp = time.now()
		self.fallback = True
		if not self.bssids.contains(bssid):
			self.bssids.append(bssid)

		self._security = Security.new_from_args(we_cipher, args)
		if not self._security:
			raise NetworkInvalidError(e)

	def read_from_config(self, config):
		try:
			self.timestamp = config.get_int(self.ssid, "timestamp")
			self.fallback = config.get_bool(self.ssid, "fallback")
		except (NoOptionError, ValueError), e:
			raise NetworkInvalidError(e)

		self._security = Security.new_from_config(config, self.ssid)
		if not self._security:
			raise NetworkInvalidError(e)

		# The following don't need to be present
		try:
			self.bssids = config.get_list(self.ssid, "bssids")
		except (NoOptionError, ValueError), e:
			pass

	def write_to_config(self, config):
		config.add_section(self.ssid)
		config.set(self.ssid, "timestamp", self.timestamp)
		config.set(self.ssid, "fallback", self.fallback)
		if len(self.bssids) > 0:
			opt = ""
			opt.join(self.bssids, " ")
			config.set(self.ssid, "bssids", opt)
		self._security.write_to_config(self.ssid, config)


class NotFoundError(dbus.DBusException):
	pass
class UnsupportedError(dbus.DBusException):
	pass

class NMInfoDBusServiceHelper(dbus.service.Object):
	def __init__(self, parent):
		self._parent = parent
		bus = dbus.SystemBus()

		# If NMI is already around, don't grab the NMI service
		bus_object = bus.get_object('org.freedesktop.DBus', '/org/freedesktop/DBus')
		name = None
		try:
			name = bus_object.GetNameOwner("org.freedesktop.NetworkManagerInfo", \
					dbus_interface='org.freedesktop.DBus')
		except dbus.DBusException:
			pass
		if name:
			print "NMI service already owned by %s, won't claim it." % name
			raise RuntimeError

		bus_name = dbus.service.BusName(NM_INFO_IFACE, bus=bus)
		dbus.service.Object.__init__(self, bus_name, NM_INFO_PATH)

	@dbus.service.method(NM_INFO_IFACE, in_signature='i', out_signature='as')
	def getNetworks(self, net_type):
		ssids = self._parent.get_networks(net_type)
		if len(ssids) > 0:
			return dbus.Array(ssids)

		raise NoNetworks

	@dbus.service.method(NM_INFO_IFACE, in_signature='si', out_signature='sibbas')
	def getNetworkProperties(self, ssid, net_type):
		props = self._parent.get_network_properties(ssid, net_type)
		if not props:
			raise NoNetworks
		return props

	@dbus.service.method(NM_INFO_IFACE)
	def updateNetworkInfo(self, ssid, bauto, bfallback, bssid, cipher, *args):
		self._parent.update_network_info(ssid, bauto, bfallback, bssid, cipher, args)

	@dbus.service.method(NM_INFO_IFACE, async_callbacks=('async_cb', 'async_err_cb'))
	def getKeyForNetwork(self, dev_path, net_path, ssid, attempt, new_key, async_cb, async_err_cb):
		self._parent.get_key_for_network(dev_path, net_path, ssid,
				attempt, new_key, async_cb, async_err_cb)

	@dbus.service.method(NM_INFO_IFACE)
	def cancelGetKeyForNetwork(self):
		self._parent.cancel_get_key_for_network()

class NMInfo(object):
	def __init__(self, client):
		try:
			profile_path = env.get_profile_path()
		except NameError:
			home = os.path.expanduser("~")
			profile_path = os.path.join(home, ".sugar", "default")
		self._cfg_file = os.path.join(profile_path, "nm", "networks.cfg")
		self._nmclient = client
		self._allowed_networks = self._read_config()
		self._dbus_helper = NMInfoDBusServiceHelper(self)

	def save_config(self):
		self._write_config(self._allowed_networks)

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
			net = Network(name)
			try:
				net.read_from_config(config)
				networks[name] = net
			except NetworkInvalidError, e:
				print "Bad network!! %s" % e
				del net
		del config
		return networks

	def _write_config(self, networks):
		fp = open(self._cfg_file, 'w')
		config = NMConfig()
		for net in networks:
			net.write_to_config(config)
		config.write(fp)
		fp.close()
		del config

	def get_networks(self, net_type):
		if net_type != NETWORK_TYPE_ALLOWED:
			raise ValueError("Bad network type")
		nets = []
		for net in self._allowed_networks:
			nets.append(net.ssid)
		print "Returning networks: %s" % nets
		return nets

	def get_network_properties(self, ssid, net_type):
		if net_type != NETWORK_TYPE_ALLOWED:
			raise ValueError("Bad network type")
		if not self._allowed_networks.has_key(ssid):
			return None
		network = self._allowed_networks[ssid]
		props = network.get_properties()
		print "Returning props for %s: %s" % (ssid, props)
		return props

	def update_network_info(self, ssid, bauto, bfallback, bssid, we_cipher, *args):
		if self._allowed_networks.has_key(ssid):
			del self._allowed_networks[ssid]
		net = Network(ssid)
		try:
			net.read_from_args(auto, fallback, bssid, we_cipher, args)
			self._allowed_networks[ssid] = net
		except InvalidNetworkError, e:
			print "Bad network!! %s" % e
			del net

	def get_key_for_network(self, dev_op, net_op, ssid, attempt, new_key, async_cb, async_err_cb):
		if self._allowed_networks.has_key(ssid) and not new_key:
			# We've got the info already
			net = self._allowed_networks[ssid]
			async_cb(tuple(net.get_security()))
			return

		# Otherwise, ask the user for it
		net = None
		dev = self._nmclient.get_device(dev_op)
		if not dev:
			async_err_cb(NotFoundError("Device was unknown."))
		if dev.get_type() == nmclient.DEVICE_TYPE_802_3_ETHERNET:
			# We don't support wired 802.1x yet...
			async_err_cb(UnsupportedError("Device type is unsupported by NMI."))

		net = dev.get_network(net_op)
		if not net:
			async_err_cb(NotFoundError("Network was unknown."))

		self._nmclient.get_key_for_network(net, async_cb, async_err_cb)

	def get_key_for_network_cb(self, key, auth_alg, async_cb, async_err_cb, canceled=False):
		"""
		Called by the NMClient when the Wireless Network Key dialog
		is closed.
		"""
		if canceled:
			e = CanceledKeyRequestError("Request was canceled.")
			# key dialog dialog was canceled; send the error back to NM
			async_err_cb(e)
			return

		if not key or not auth_alg:
			# no key returned, *** BUG ***; the key dialog
			# should always return either a key + auth_alg, or a
			#cancel error
			raise RuntimeError("No key or auth alg given! Bug!")

		we_cipher = None
		if len(key) == 26:
			we_cipher = IW_AUTH_CIPHER_WEP104
		elif len(key) == 10:
			we_cipher = IW_AUTH_CIPHER_WEP40
		else:
			raise RuntimeError("Invalid key length!")

		# Stuff the returned key and auth algorithm into a security object
		# and return it to NetworkManager
		sec = Security.new_from_args(we_cipher, key, auth_alg)
		props = sec.get_properties()
		a = tuple(props)
		async_cb(*a)

	def cancel_get_key_for_network(self):
		# Tell the NMClient to close the key request dialog
		self._nmclient.cancel_get_key_for_network()
