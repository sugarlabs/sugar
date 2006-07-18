import avahi
import sys, os
sys.path.insert(0, os.path.abspath("../../"))
from sugar import util
import dbus, dbus.service

def _txt_to_dict(txt):
	"""Convert an avahi-returned TXT record formatted
	as nested arrays of integers (from dbus) into a dict
	of key/value string pairs."""
	prop_dict = {}
	props = avahi.txt_array_to_string_array(txt)
	for item in props:
		key = value = None
		if '=' not in item:
			# No = means a boolean value of true
			key = item
			value = True
		else:
			(key, value) = item.split('=')
		prop_dict[key] = value
	return prop_dict

def compose_service_name(name, activity_id):
	if not name:
		raise ValueError("name must be a valid string.")
	if not activity_id:
		return name
	if type(name) != type(u""):
		raise ValueError("name must be in unicode.")
	composed = "%s [%s]" % (name, activity_id)
	return composed.encode()

def _decompose_service_name(name):
	"""Break a service name into the name and activity ID, if we can."""
	if type(name) != type(u""):
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

def is_multicast_address(address):
	"""Simple numerical check for whether an IP4 address
	is in the range for multicast addresses or not."""
	if not address:
		return False
	if address[3] != '.':
		return False
	first = int(address[:3])
	if first >= 224 and first <= 239:
		return True
	return False

def deserialize(sdict):
	try:
		name = sdict['name']
		if type(name) != type(u""):
			raise ValueError("name must be unicode.")
		stype = sdict['stype']
		if type(stype) != type(u""):
			raise ValueError("type must be unicode.")
		domain = sdict['domain']
		if type(domain) != type(u""):
			raise ValueError("domain must be unicode.")
		port = sdict['port']
		properties = sdict['properties']
	except KeyError, exc:
		raise ValueError("Serialized service object was not valid.")

	address = None
	try:
		address = sdict['address']
		if type(address) != type(u""):
			raise ValueError("address must be unicode.")
	except KeyError:
		pass
	
	activity_id = None
	try:
		activity_id = sdict['activity_id']
		if type(activity_id) != type(u""):
			raise ValueError("activity id must be unicode.")
	except KeyError:
		pass

	if activity_id is not None:
		name = compose_service_name(name, activity_id)

	return Service(name, stype, domain, address=address,
		port=port, properties=properties)


_ACTIVITY_ID_TAG = "ActivityID"
SERVICE_DBUS_INTERFACE = "org.laptop.Presence.Service"

class ServiceDBusHelper(dbus.service.Object):
	"""Handle dbus requests and signals for Service objects"""
	def __init__(self, parent, bus_name, object_path):
		self._parent = parent
		self._bus_name = bus_name
		self._object_path = object_path
		dbus.service.Object.__init__(self, bus_name, self._object_path)

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						in_signature="", out_signature="a{sv}")
	def getProperties(self):
		"""Return service properties."""
		pary = {}
		pary['name'] = self._parent.get_name()
		pary['type'] = self._parent.get_type()
		pary['domain'] = self._parent.get_domain()
		pary['activityId'] = self._parent.get_activity_id()
		port = self._parent.get_port()
		if port:
			pary['port'] = self._parent.get_port()
		addr = self._parent.get_address()
		if addr:
			pary['address'] = addr
		source_addr = self._parent.get_publisher_address()
		if source_addr:
			pary['sourceAddress'] = source_addr
		return pary

	@dbus.service.method(SERVICE_DBUS_INTERFACE,
						in_signature="s", out_signature="s")
	def getPublishedValue(self, key):
		"""Return the value belonging to the requested key from the
		service's TXT records."""
		value = self._parent.get_one_property(key)
		if type(value) == type(True):
			value = str(value)
		return value

class Service(object):
	"""Encapsulates information about a specific ZeroConf/mDNS
	service as advertised on the network."""
	def __init__(self, bus_name, object_id, name, stype, domain, address=None, port=-1, properties=None):
		if not bus_name:
			raise ValueError("DBus bus name must be valid")
		if not object_id or type(object_id) != type(1):
			raise ValueError("object id must be a valid number")

		# Validate immutable options
		if name and type(name) != type(u""):
			raise ValueError("name must be unicode.")
		if not name or not len(name):
			raise ValueError("must specify a valid service name.")

		if stype and type(stype) != type(u""):
			raise ValueError("service type must be in unicode.")
		if not stype or not len(stype):
			raise ValueError("must specify a valid service type.")
		if not stype.endswith("._tcp") and not stype.endswith("._udp"):
			raise ValueError("must specify a TCP or UDP service type.")

		if domain and type(domain) != type(u""):
			raise ValueError("domain must be in unicode.")
		if len(domain) and domain != "local":
			raise ValueError("must use the 'local' domain (for now).")

		(actid, real_name) = _decompose_service_name(name)
		self._name = real_name
		self._stype = stype
		self._domain = domain
		self._port = -1
		self.set_port(port)
		self._properties = {}
		self.set_properties(properties)
		# Publisher address is the unicast source IP
		self._publisher_address = address
		# Address is the published address, could be multicast or unicast
		self._address = None
		if self._properties.has_key('address'):
			self.set_address(self._properties['address'])
		else:
			self.set_address(address)

		# Ensure that an ActivityID tag, if given, matches
		# what we expect from the service type
		if self._properties.has_key(_ACTIVITY_ID_TAG):
			prop_actid = self._properties[_ACTIVITY_ID_TAG]
			if (prop_actid and not actid) or (prop_actid != actid):
				raise ValueError("ActivityID property specified, but the service names's activity ID didn't match it: %s, %s" % (prop_actid, actid))
		self._activity_id = actid
		if actid and not self._properties.has_key(_ACTIVITY_ID_TAG):
			self._properties[_ACTIVITY_ID_TAG] = actid

		# register ourselves with dbus
		self._object_id = object_id
		self._object_path = "/org/laptop/Presence/Services/%d" % self._object_id
		self._dbus_helper = ServiceDBusHelper(self, bus_name, self._object_path)

	def object_path(self):
		return self._object_path

	def serialize(self, owner=None):
		sdict = {}
		if owner is not None:
			sdict['name'] = dbus.Variant(owner.get_nick_name())
		else:
			sdict['name'] = dbus.Variant(self._name)
		sdict['stype'] = dbus.Variant(self._stype)
		if self._activity_id:
			sdict['activity_id'] = dbus.Variant(self._activity_id)
		sdict['domain'] = dbus.Variant(self._domain)
		if self._address:
			sdict['address'] = dbus.Variant(self._address)
		sdict['port'] = dbus.Variant(self._port)
		sdict['properties'] = dbus.Variant(self._properties)
		return sdict

	def get_name(self):
		"""Return the service's name, usually that of the
		buddy who provides it."""
		return self._name

	def is_multicast_service(self):
		"""Return True if the service's address is a multicast address,
		False if it is not."""
		return is_multicast_address(self._address)

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

	def set_properties(self, properties):
		"""Set the service's properties from either an Avahi
		TXT record (a list of lists of integers), or a
		python dictionary."""
		self._properties = {}
		props = {}
		if type(properties) == type([]):
			props = _txt_to_dict(properties)
		elif type(properties) == type({}):
			props = properties

		# Set key/value pairs on internal property list, 
		# also convert everything to local encoding (for now)
		# to ensure consistency
		for key, value in props.items():
			tmp_key = key
			tmp_val = value
			if type(tmp_key) == type(u""):
				tmp_key = tmp_key.encode()
			if type(tmp_val) == type(u""):
				tmp_val = tmp_val.encode()
			self._properties[tmp_key] = tmp_val

	def get_type(self):
		"""Return the service's service type."""
		return self._stype

	def get_activity_id(self):
		"""Return the activity ID this service is associated with, if any."""
		return self._activity_id

	def get_port(self):
		return self._port

	def set_port(self, port):
		if type(port) != type(1) or (port <= 1024 and port > 65536):
			raise ValueError("must specify a valid port number between 1024 and 65536.")
		self._port = port

	def get_publisher_address(self):
		return self._publisher_address

	def get_address(self):
		return self._address

	def set_address(self, address):
		if address is not None:
			if type(address) != type(u""):
				raise ValueError("address must be unicode")
		self._address = address

	def get_domain(self):
		"""Return the ZeroConf/mDNS domain the service was found in."""
		return self._domain


#################################################################
# Tests
#################################################################

import unittest

class ServiceTestCase(unittest.TestCase):
	_DEF_NAME = u"foobar"
	_DEF_STYPE = u"_foo._bar._tcp"
	_DEF_DOMAIN = u"local"
	_DEF_ADDRESS = u"1.1.1.1"
	_DEF_PORT = 1234
	_DEF_PROPS = {'foobar': 'baz'}
	
	_STR_TEST_ARGS = [None, 0, [], {}]

	def _test_init_fail(self, name, stype, domain, address, port, properties, fail_msg):
		"""Test something we expect to fail."""
		try:
			service = Service(name, stype, domain, address, port, properties)
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
		self._test_init_fail(self._DEF_NAME, "_bork._foobar", self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS, "invalid service type")

	def testDomain(self):
		for item in self._STR_TEST_ARGS:
			self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, item, self._DEF_ADDRESS,
					self._DEF_PORT, self._DEF_PROPS, "invalid domain")
		# Only accept local for now
		self._test_init_fail(self._DEF_NAME, self._DEF_STYPE, "foobar", self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS, "invalid domain")
		# Make sure "" works
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('org.laptop.Presence', bus=session_bus)		
		service = Service(bus_name, 1, self._DEF_NAME, self._DEF_STYPE, "", self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS)
		del bus_name, session_bus
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
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('org.laptop.Presence', bus=session_bus)		
		service = Service(bus_name, 1, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS)
		del bus_name, session_bus
		assert service.get_name() == self._DEF_NAME, "service name wasn't correct after init."
		assert service.get_type() == self._DEF_STYPE, "service type wasn't correct after init."
		assert service.get_domain() == "local", "service domain wasn't correct after init."
		assert service.get_address() == self._DEF_ADDRESS, "service address wasn't correct after init."
		assert service.get_port() == self._DEF_PORT, "service port wasn't correct after init."
		value = service.get_one_property('foobar')
		assert value and value == 'baz', "service property wasn't correct after init."

	def testAvahiProperties(self):
		props = [[111, 114, 103, 46, 102, 114, 101, 101, 100, 101, 115, 107, 116, 111, 112, 46, 65, 118, 97, 104, 105, 46, 99, 111, 111, 107, 105, 101, 61, 50, 54, 48, 49, 53, 52, 51, 57, 53, 50]]
		key = "org.freedesktop.Avahi.cookie"
		expected_value = "2601543952"
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('org.laptop.Presence', bus=session_bus)		
		service = Service(bus_name, 1, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, props)
		del bus_name, session_bus
		value = service.get_one_property(key)
		assert value and value == expected_value, "service properties weren't correct after init."
		value = service.get_one_property('bork')
		assert not value, "service properties weren't correct after init."

	def testBoolProperty(self):
		props = [[111, 114, 103, 46, 102, 114, 101, 101, 100, 101, 115, 107, 116, 111, 112, 46, 65, 118, 97, 104, 105, 46, 99, 111, 111, 107, 105, 101]]
		key = "org.freedesktop.Avahi.cookie"
		expected_value = True
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('org.laptop.Presence', bus=session_bus)		
		service = Service(bus_name, 1, self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, props)
		value = service.get_one_property(key)
		del bus_name, session_bus
		assert value is not None and value == expected_value, "service properties weren't correct after init."

	def testGroupService(self):
		# Valid group service type, non-multicast address
		group_stype = u"_af5e5a7c998e89b9a_group_olpc._udp"
		self._test_init_fail(self._DEF_NAME, group_stype, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS, "group service type, but non-multicast address")

		# Valid group service type, None address
		session_bus = dbus.SessionBus()
		bus_name = dbus.service.BusName('org.laptop.Presence', bus=session_bus)		
		service = Service(bus_name, 1, self._DEF_NAME, group_stype, self._DEF_DOMAIN, None,
				self._DEF_PORT, self._DEF_PROPS)
		assert service.get_address() == None, "address was not None as expected!"

		# Valid group service type and multicast address, ensure it works
		mc_addr = u"224.0.0.34"
		service = Service(bus_name, 1, self._DEF_NAME, group_stype, self._DEF_DOMAIN, mc_addr,
				self._DEF_PORT, self._DEF_PROPS)
		del bus_name, session_bus
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
		suite.addTest(ServiceTestCase("testGroupService"))
	addToSuite = staticmethod(addToSuite)


def main():
	suite = unittest.TestSuite()
	ServiceTestCase.addToSuite(suite)
	runner = unittest.TextTestRunner()
	runner.run(suite)

if __name__ == "__main__":
	main()
