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

import avahi
import sys, os
sys.path.insert(0, os.path.abspath("../../"))
from sugar import util
import dbus, dbus.service
import random
import logging
import gobject

def compose_service_name(name, activity_id):
	if isinstance(name, str):
		name = unicode(name)
	if not name:
		raise ValueError("name must be a valid string.")
	if not activity_id:
		return name
	if not isinstance(name, unicode):
		raise ValueError("name must be in unicode.")
	composed = "%s [%s]" % (name, activity_id)
	return composed

def decompose_service_name(name):
	"""Break a service name into the name and activity ID, if we can."""
	if not isinstance(name, unicode):
		raise ValueError("name must be a valid unicode string.")
	name_len = len(name)
	if name_len < util.ACTIVITY_ID_LEN + 5:
		return (None, name)
	# check for activity id end marker
	if name[name_len - 1] != "]":
		return (None, name)
	start = name_len - 1 - util.ACTIVITY_ID_LEN
	end = name_len - 1
	# check for activity id start marker
	if name[start - 1] != "[" or name[start - 2] != " ":
		return (None, name)
	activity_id = name[start:end]
	if not util.validate_activity_id(activity_id):
		return (None, name)
	return (activity_id, name[:start - 2])

def _one_dict_differs(dict1, dict2):
	diff_keys = []
	for key, value in dict1.items():
		if not dict2.has_key(key) or dict2[key] != value:
			diff_keys.append(key)
	return diff_keys

def _dicts_differ(dict1, dict2):
	diff_keys = []
	diff1 = _one_dict_differs(dict1, dict2)
	diff2 = _one_dict_differs(dict2, dict1)
	for key in diff2:
		if key not in diff1:
			diff_keys.append(key)
	diff_keys += diff1
	return diff_keys

def _convert_properties_to_dbus_byte_array(props):
	# Ensure properties are converted to ByteArray types
	# because python sometimes can't figure that out
	info = dbus.Array([], signature="aay")
	for k, v in props.items():
		info.append(dbus.types.ByteArray("%s=%s" % (k, v)))
	return info


_ACTIVITY_ID_TAG = "ActivityID"
SERVICE_DBUS_INTERFACE = "org.laptop.Presence.Service"
SERVICE_DBUS_OBJECT_PATH = "/org/laptop/Presence/Services/"

class ServiceDBusHelper(dbus.service.Object):
	"""Handle dbus requests and signals for Service objects"""
	def __init__(self, parent, bus_name, object_path):
		self._parent = parent
		self._bus_name = bus_name
		self._object_path = object_path
		dbus.service.Object.__init__(self, bus_name, self._object_path)

	@dbus.service.signal(SERVICE_DBUS_INTERFACE,
						signature="as")
	def PublishedValueChanged(self, keylist):
		pass

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						in_signature="", out_signature="a{sv}")
	def getProperties(self):
		"""Return service properties."""
		pary = {}
		pary['name'] = self._parent.get_name()
		pary['type'] = self._parent.get_type()
		pary['domain'] = self._parent.get_domain()
		actid = self._parent.get_activity_id()
		if actid:
			pary['activityId'] = actid
		port = self._parent.get_port()
		if port:
			pary['port'] = self._parent.get_port()
		addr = self._parent.get_address()
		if addr:
			pary['address'] = addr
		source_addr = self._parent.get_source_address()
		if source_addr:
			pary['sourceAddress'] = source_addr
		return pary

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						in_signature="s")
	def getPublishedValue(self, key):
		"""Return the value belonging to the requested key from the
		service's TXT records."""
		val = self._parent.get_one_property(key)
		if not val:
			raise KeyError("Value was not found.")
		return val

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						in_signature="", out_signature="a{sv}")
	def getPublishedValues(self):
		pary = {}
		props = self._parent.get_properties()
		for key, value in props.items():
			pary[key] = str(value)
		return dbus.Dictionary(pary)

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						sender_keyword="sender")
	def setPublishedValue(self, key, value, sender):
		self._parent.set_property(key, value, sender)

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						in_signature="a{sv}", sender_keyword="sender")
	def setPublishedValues(self, values, sender):
		if not self._parent.is_local():
			raise ValueError("Service was not not registered by requesting process!")		
		self._parent.set_properties(values, sender)


class Service(gobject.GObject):
	"""Encapsulates information about a specific ZeroConf/mDNS
	service as advertised on the network."""

	__gsignals__ = {
		'property-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, bus_name, object_id, name, stype, domain=u"local",
				address=None, port=-1, properties=None, source_address=None,
				local_publisher=None):
		gobject.GObject.__init__(self)
		if not bus_name:
			raise ValueError("DBus bus name must be valid")
		if not object_id or not isinstance(object_id, int):
			raise ValueError("object id must be a valid number")

		# Validate immutable options
		if name and not isinstance(name, unicode):
			raise ValueError("name must be unicode.")
		if not name or not len(name):
			raise ValueError("must specify a valid service name.")

		if stype and not isinstance(stype, unicode):
			raise ValueError("service type must be in unicode.")
		if not stype or not len(stype):
			raise ValueError("must specify a valid service type.")
		if not stype.endswith("._tcp") and not stype.endswith("._udp"):
			raise ValueError("must specify a TCP or UDP service type.")

		if not isinstance(domain, unicode):
			raise ValueError("domain must be in unicode.")
		if domain and domain != "local":
			raise ValueError("must use the 'local' domain (for now).")

		# ID of the D-Bus connection that published this service, if any.
		# We only let the local publisher modify the service.
		self._local_publisher = local_publisher

		self._avahi_entry_group = None

		(actid, real_name) = decompose_service_name(name)
		self._name = real_name
		self._full_name = name
		self._stype = stype
		self._domain = domain
		self._port = -1
		self.set_port(port)
		self._properties = {}
		self._dbus_helper = None
		self._internal_set_properties(properties)

		# Source address is the unicast source IP
		self._source_address = None
		if source_address is not None:
			self.set_source_address(source_address)

		# Address is the published address, could be multicast or unicast
		self._address = None
		if self._properties.has_key('address'):
			self.set_address(self._properties['address'])
		elif address is not None:
			self.set_address(address)
			self._properties['address'] = address

		# Ensure that an ActivityID tag, if given, matches
		# what we expect from the service type
		if self._properties.has_key(_ACTIVITY_ID_TAG):
			prop_actid = self._properties[_ACTIVITY_ID_TAG]
			if (prop_actid and not actid) or (prop_actid != actid):
				raise ValueError("ActivityID property specified, but the " \
						"service names's activity ID didn't match it: %s," \
						" %s" % (prop_actid, actid))
		self._activity_id = actid
		if actid and not self._properties.has_key(_ACTIVITY_ID_TAG):
			self._properties[_ACTIVITY_ID_TAG] = actid

		self._owner = None

		# register ourselves with dbus
		self._object_id = object_id
		self._object_path = SERVICE_DBUS_OBJECT_PATH + str(self._object_id)
		self._dbus_helper = ServiceDBusHelper(self, bus_name, self._object_path)

	def object_path(self):
		return dbus.ObjectPath(self._object_path)

	def get_owner(self):
		return self._owner

	def set_owner(self, owner):
		if self._owner is not None:
			raise RuntimeError("Can only set a service's owner once")
		self._owner = owner

	def is_local(self):
		if self._local_publisher is not None:
			return True
		return False

	def get_name(self):
		"""Return the service's name, usually that of the
		buddy who provides it."""
		return self._name

	def get_full_name(self):
		return self._full_name

	def get_one_property(self, key):
		"""Return one property of the service, or None
		if the property was not found.  Cannot distinguish
		between lack of a property, and a property value that
		actually is None."""
		if key in self._properties.keys():
			return self._properties[key]
		return None

	def get_properties(self):
		"""Return a python dictionary of all the service's
		properties."""
		return self._properties

	def __emit_properties_changed_signal(self, keys):
		if self._dbus_helper:
			self._dbus_helper.PublishedValueChanged(keys)
		self.emit('property-changed', keys)

	def set_property(self, key, value, sender=None):
		"""Set one service property"""
		if not self._local_publisher:
			raise ValueError("Service was not not registered by requesting process!")		
		if sender is not None and self._local_publisher != sender:
			raise ValueError("Service was not not registered by requesting process!")

		if not isinstance(key, unicode):
			raise ValueError("Key must be a unicode string.")
		if not isinstance(value, unicode) and not isinstance(value, bool):
			raise ValueError("Key must be a unicode string or a boolean.")

		# Ignore setting the key to it's current value
		if self._properties.has_key(key):
			if self._properties[key] == value:
				return

		# Blank value means remove key
		remove = False
		if isinstance(value, unicode) and len(value) == 0:
			remove = True
		if isinstance(value, bool) and value == False:
			remove = True

		if remove:
			# If the key wasn't present, return without error
			if self._properties.has_key(key):
				del self._properties[key]
		else:
			# Otherwise set it
			if isinstance(value, bool):
				value = ""
			self._properties[key] = value

		# if the service is locally published already, update the TXT records
		if self._local_publisher and self._avahi_entry_group:
			self.__internal_update_avahi_properties()

		self.__emit_properties_changed_signal([key])

	def set_properties(self, properties, sender=None, from_network=False):
		"""Set all service properties in one call"""
		if sender is not None and self._local_publisher != sender:
			raise ValueError("Service was not not registered by requesting process!")

		self._internal_set_properties(properties, from_network)

	def _internal_set_properties(self, properties, from_network=False):
		"""Set the service's properties from either an Avahi
		TXT record (a list of lists of integers), or a
		python dictionary."""
		if not isinstance (properties, dict):
			raise ValueError("Properties must be a dictionary.")

		# Make sure the properties are actually different
		diff_keys = _dicts_differ(self._properties, properties)
		if len(diff_keys) == 0:
			return

		self._properties = {}
		# Set key/value pairs on internal property list
		for key, value in properties.items():
			if len(key) == 0:
				continue
			tmp_key = key
			tmp_val = value
			if not isinstance(tmp_key, unicode):
				tmp_key = unicode(tmp_key)
			if not isinstance(tmp_val, unicode):
				tmp_val = unicode(tmp_val)
			self._properties[tmp_key] = tmp_val

		# if the service is locally published already, update the TXT records
		if self._local_publisher and self._avahi_entry_group and not from_network:
			self.__internal_update_avahi_properties()

		self.__emit_properties_changed_signal(diff_keys)

	def __internal_update_avahi_properties(self):
		info = _convert_properties_to_dbus_byte_array(self._properties)
		self._avahi_entry_group.UpdateServiceTxt(avahi.IF_UNSPEC,
				avahi.PROTO_UNSPEC, 0,
				dbus.String(self._full_name), dbus.String(self._stype),
				dbus.String(self._domain), info)

	def get_type(self):
		"""Return the service's service type."""
		return self._stype

	def get_activity_id(self):
		"""Return the activity ID this service is associated with, if any."""
		return self._activity_id

	def get_port(self):
		return self._port

	def set_port(self, port):
		if not isinstance(port, int) or (port <= 1024 and port > 65536):
			raise ValueError("must specify a valid port number between 1024 and 65536.")
		self._port = port

	def get_source_address(self):
		return self._source_address

	def set_source_address(self, address):
		if not address or not isinstance(address, unicode):
			raise ValueError("address must be unicode")
		self._source_address = address

	def get_address(self):
		return self._address

	def set_address(self, address):
		if not address or not isinstance(address, unicode):
			raise ValueError("address must be a unicode string")
		self._address = address
		self._properties['address'] = address

	def get_domain(self):
		"""Return the ZeroConf/mDNS domain the service was found in."""
		return self._domain

	def register(self, system_bus, avahi_service):
		if self._avahi_entry_group is not None:
			raise RuntimeError("Service already registered!")

		obj = system_bus.get_object(avahi.DBUS_NAME, avahi_service.EntryGroupNew())
		self._avahi_entry_group = dbus.Interface(obj, avahi.DBUS_INTERFACE_ENTRY_GROUP)

		info = _convert_properties_to_dbus_byte_array(self._properties)
		logging.debug("Will register service with name='%s', stype='%s'," \
				" domain='%s', address='%s', port=%d, info='%s'" % (self._full_name,
				self._stype, self._domain, self._address, self._port, info))

		self._avahi_entry_group.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, 0,
				dbus.String(self._full_name), dbus.String(self._stype),
				dbus.String(self._domain), dbus.String(""), # let Avahi figure the 'host' out
				dbus.UInt16(self._port), info)

		self._avahi_entry_group.connect_to_signal('StateChanged', self.__entry_group_changed_cb)
		self._avahi_entry_group.Commit()

	def __entry_group_changed_cb(self, state, error):
		pass
#		logging.debug("** %s.%s Entry group changed: state %s, error %s" % (self._full_name, self._stype, state, error))

	def unregister(self, sender):
		# Refuse to unregister if we can't get the dbus connection this request
		# came from for some reason
		if not sender:
			raise RuntimeError("Service registration request must have a sender.")
		if not self._local_publisher:
			raise ValueError("Service was not a local service provided by this laptop!")
		if sender is not None and self._local_publisher != sender:
			raise ValueError("Service was not registered by requesting process!")
		if not self._avahi_entry_group:
			raise ValueError("Service was not registered by requesting process!")
 		self._avahi_entry_group.Free()
		del self._avahi_entry_group
		self._avahi_entry_group = None


#################################################################
# Tests
#################################################################

import unittest

__objid_seq = 0
def _next_objid():
	global __objid_seq
	__objid_seq = __objid_seq + 1
	return __objid_seq


class ServiceTestCase(unittest.TestCase):
	_DEF_NAME = u"foobar"
	_DEF_STYPE = u"_foo._bar._tcp"
	_DEF_DOMAIN = u"local"
	_DEF_ADDRESS = u"1.1.1.1"
	_DEF_PORT = 1234
	_DEF_PROPS = {'foobar': 'baz'}
	_STR_TEST_ARGS = [None, 0, [], {}]

	def __init__(self, name):
		self._bus = dbus.SessionBus()
		self._bus_name = dbus.service.BusName('org.laptop.Presence', bus=self._bus)		
		unittest.TestCase.__init__(self, name)

	def __del__(self):
		del self._bus_name
		del self._bus

	def _test_init_fail(self, name, stype, domain, address, port, properties, fail_msg):
		"""Test something we expect to fail."""
		try:
			objid = _next_objid()
			service = Service(self._bus_name, objid, name, stype, domain, address,
					port, properties)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError for %s." % fail_msg)

	def testName(self):
		for item in self._STR_TEST_ARGS:
			self._test_init_fail(item, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
					self._DEF_PORT, self._DEF_PROPS, "invalid name")

	def testType(self):
		for item in self._STR_TEST_ARGS:
			self._test_init_fail(self._DEF_NAME, item, self._DEF_DOMAIN, self._DEF_ADDRESS,
					self._DEF_PORT, self._DEF_PROPS, "invalid service type")
		self._test_init_fail(self._DEF_NAME, u"_bork._foobar", self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS, "invalid service type")

	def testDomain(self):
		for item in self._STR_TEST_ARGS:
			self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, item, self._DEF_ADDRESS,
					self._DEF_PORT, self._DEF_PROPS, "invalid domain")
		# Only accept local for now
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, u"foobar", self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS, "invalid domain")
		# Make sure "" works
		objid = _next_objid()
		service = Service(self._bus_name, objid, self._DEF_NAME, self._DEF_STYPE, u"",
				self._DEF_ADDRESS, self._DEF_PORT, self._DEF_PROPS)
		assert service, "Empty domain was not accepted!"

	def testAddress(self):
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, [],
				self._DEF_PORT, self._DEF_PROPS, "invalid address")
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, {},
				self._DEF_PORT, self._DEF_PROPS, "invalid address")
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, 1234,
				self._DEF_PORT, self._DEF_PROPS, "invalid address")

	def testPort(self):
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				[], self._DEF_PROPS, "invalid port")
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				{}, self._DEF_PROPS, "invalid port")
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				"adf", self._DEF_PROPS, "invalid port")

	def testGoodInit(self):
		objid = _next_objid()
		service = Service(self._bus_name, objid, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN,
				self._DEF_ADDRESS, self._DEF_PORT, self._DEF_PROPS)
		assert service.get_name() == self._DEF_NAME, "service name wasn't correct after init."
		assert service.get_type() == self._DEF_STYPE, "service type wasn't correct after init."
		assert service.get_domain() == "local", "service domain wasn't correct after init."
		assert service.get_address() == self._DEF_ADDRESS, "service address wasn't correct after init."
		assert service.get_port() == self._DEF_PORT, "service port wasn't correct after init."
		assert service.object_path() == SERVICE_DBUS_OBJECT_PATH + str(objid)
		value = service.get_one_property('foobar')
		assert value and value == 'baz', "service property wasn't correct after init."

	def testAvahiProperties(self):
		props = [[111, 114, 103, 46, 102, 114, 101, 101, 100, 101, 115, 107, 116, 111, 112, 46, 65, 118, 97, 104, 105, 46, 99, 111, 111, 107, 105, 101, 61, 50, 54, 48, 49, 53, 52, 51, 57, 53, 50]]
		key = "org.freedesktop.Avahi.cookie"
		expected_value = "2601543952"
		objid = _next_objid()
		service = Service(self._bus_name, objid, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN,
				self._DEF_ADDRESS, self._DEF_PORT, props)
		value = service.get_one_property(key)
		assert value and value == expected_value, "service properties weren't correct after init."
		value = service.get_one_property('bork')
		assert not value, "service properties weren't correct after init."

	def testBoolProperty(self):
		props = [[111, 114, 103, 46, 102, 114, 101, 101, 100, 101, 115, 107, 116, 111, 112, 46, 65, 118, 97, 104, 105, 46, 99, 111, 111, 107, 105, 101]]
		key = "org.freedesktop.Avahi.cookie"
		expected_value = True
		objid = _next_objid()
		service = Service(self._bus_name, objid, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, props)
		value = service.get_one_property(key)
		assert value is not None and value == expected_value, "service properties weren't correct after init."

	def testActivityService(self):
		# Valid group service type, non-multicast address
		actid = "4569a71b80805aa96a847f7ac1c407327b3ec2b4"
		name = compose_service_name("Tommy", actid)

		# Valid activity service name, None address
		objid = _next_objid()
		service = Service(self._bus_name, objid, name, self._DEF_STYPE, self._DEF_DOMAIN, None,
				self._DEF_PORT, self._DEF_PROPS)
		assert service.get_address() == None, "address was not None as expected!"
		assert service.get_activity_id() == actid, "activity id was different than expected!"

		# Valid activity service name and multicast address, ensure it works
		mc_addr = u"224.0.0.34"
		objid = _next_objid()
		service = Service(self._bus_name, objid, name, self._DEF_STYPE, self._DEF_DOMAIN, mc_addr,
				self._DEF_PORT, self._DEF_PROPS)
		assert service.get_address() == mc_addr, "address was not expected address!"

	def addToSuite(suite):
		suite.addTest(ServiceTestCase("testName"))
		suite.addTest(ServiceTestCase("testType"))
		suite.addTest(ServiceTestCase("testDomain"))
		suite.addTest(ServiceTestCase("testAddress"))
		suite.addTest(ServiceTestCase("testPort"))
		suite.addTest(ServiceTestCase("testGoodInit"))
		suite.addTest(ServiceTestCase("testAvahiProperties"))
		suite.addTest(ServiceTestCase("testBoolProperty"))
		suite.addTest(ServiceTestCase("testActivityService"))
	addToSuite = staticmethod(addToSuite)


def main():
	suite = unittest.TestSuite()
	ServiceTestCase.addToSuite(suite)
	runner = unittest.TextTestRunner()
	runner.run(suite)

if __name__ == "__main__":
	main()
