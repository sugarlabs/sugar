import avahi
from sugar import util
import string

def new_group_service(group_name, resource):
	"""Create a new service suitable for defining a new group."""
	if type(group_name) != type("") or not len(group_name):
		raise ValueError("group name must be a valid string.")
	if type(resource) != type("") or not len(resource):
		raise ValueError("group resource must be a valid string.")

	# Create a randomized service type
	data = "%s%s" % (group_name, resource)
	stype = "_%s_group_olpc._udp" % sugar.util.unique_id(data)

	properties = {__GROUP_NAME_TAG: group_name, __GROUP_RESOURCE_TAG: resource }
	owner_nick = ""
	port = random.randint(5000, 65000)
	# Use random currently unassigned multicast address
	address = "232.%d.%d.%d" % (random.randint(0, 254), random.randint(1, 254),
			random.randint(1, 254))
	service = Service.Service(owner_nick, stype, "local", address=address,
			port=port, properties=properties)
	return service


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

def _decompose_service_type(stype):
	"""Break a service type into the UID and real service type, if we can."""
	if len(stype) < util.ACTIVITY_UID_LEN + 5:
		return (None, stype)
	if stype[0] != "_":
		return (None, stype)
	start = 1
	end = start + util.ACTIVITY_UID_LEN
	if stype[end] != "_":
		return (None, stype)
	uid = stype[start:end]
	if not util.validate_activity_uid(uid):
		return (None, stype)
	return (uid, stype[end:])

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


_ACTIVITY_UID_TAG = "ActivityUID"

class Service(object):
	"""Encapsulates information about a specific ZeroConf/mDNS
	service as advertised on the network."""
	def __init__(self, name, stype, domain, address=None, port=-1, properties=None):
		# Validate immutable options
		if not name or (type(name) != type("") and type(name) != type(u"")) or not len(name):
			raise ValueError("must specify a valid service name.")

		if not stype or (type(stype) != type("") and type(stype) != type(u"")) or not len(stype):
			raise ValueError("must specify a service type.")
		if not stype.endswith("._tcp") and not stype.endswith("._udp"):
			raise ValueError("must specify a TCP or UDP service type.")

		if type(domain) != type("") and type(domain) != type(u""):
			raise ValueError("must specify a domain.")
		if len(domain) and domain != "local" and domain != u"local":
			raise ValueError("must use the 'local' domain (for now).")

		(uid, real_stype) = _decompose_service_type(stype)
		if uid and not util.validate_activity_uid(activity_uid):
			raise ValueError("activity_uid not a valid activity UID.")
		
		self._name = name
		self._stype = stype
		self._real_stype = real_stype
		self._domain = domain
		self._address = None
		self.set_address(address)
		self._port = -1
		self.set_port(port)
		self._properties = {}
		self.set_properties(properties)

		# Ensure that an ActivityUID tag, if given, matches
		# what we expect from the service type
		if self._properties.has_key(_ACTIVITY_UID_TAG):
			prop_uid = self._properties[_ACTIVITY_UID_TAG]
			if (prop_uid and not uid) or (prop_uid != uid):
				raise ValueError("ActivityUID property specified, but the service type's activity UID didn't match it.")
		self._activity_uid = uid
		if uid and not self._properties.has_key(_ACTIVITY_UID_TAG):
			self._properties[_ACTIVITY_UID_TAG] = uid

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
		if type(properties) == type([]):
			self._properties = _txt_to_dict(properties)
		elif type(properties) == type({}):
			self._properties = properties

	def get_type(self):
		"""Return the service's service type."""
		return self._stype

	def get_network_type(self):
		"""Return the full service type, including activity UID."""
		return self._real_stype

	def get_port(self):
		return self._port

	def set_port(self, port):
		if type(port) != type(1):
			raise ValueError("must specify a valid port number.")
		self._port = port

	def get_address(self):
		return self._address

	def set_address(self, address):
		if address is not None:
			if type(address) != type("") and type(address) != type(u""):
				raise ValueError("must specify a valid address.")
			if not len(address):
				raise ValueError("must specify a valid address.")
		self._address = address

	def get_domain(self):
		"""Return the ZeroConf/mDNS domain the service was found in."""
		return self._domain

	def get_activity_uid(self):
		"""Return the activity UID this service is associated with, if any."""
		return self._activity_uid


#################################################################
# Tests
#################################################################

import unittest

class ServiceTestCase(unittest.TestCase):
	_DEF_NAME = "foobar"
	_DEF_STYPE = "_foo._bar._tcp"
	_DEF_DOMAIN = "local"
	_DEF_ADDRESS = "1.1.1.1"
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
		service = Service(self._DEF_NAME, self._DEF_STYPE, "", self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS)
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
		service = Service(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS)
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
		service = Service(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, props)
		value = service.get_one_property(key)
		assert value and value == expected_value, "service properties weren't correct after init."
		value = service.get_one_property('bork')
		assert not value, "service properties weren't correct after init."

	def testBoolProperty(self):
		props = [[111, 114, 103, 46, 102, 114, 101, 101, 100, 101, 115, 107, 116, 111, 112, 46, 65, 118, 97, 104, 105, 46, 99, 111, 111, 107, 105, 101]]
		key = "org.freedesktop.Avahi.cookie"
		expected_value = True
		service = Service(self._DEF_NAME, self._DEF_STYPE, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, props)
		value = service.get_one_property(key)
		assert value is not None and value == expected_value, "service properties weren't correct after init."

	def testGroupService(self):
		# Valid group service type, non-multicast address
		group_stype = "_af5e5a7c998e89b9a_group_olpc._udp"
		self._test_init_fail(self._DEF_NAME, group_stype, self._DEF_DOMAIN, self._DEF_ADDRESS,
				self._DEF_PORT, self._DEF_PROPS, "group service type, but non-multicast address")

		# Valid group service type, None address
		service = Service(self._DEF_NAME, group_stype, self._DEF_DOMAIN, None,
				self._DEF_PORT, self._DEF_PROPS)
		assert service.get_address() == None, "address was not None as expected!"
		# Set address to invalid multicast address
		try:
			service.set_address(self._DEF_ADDRESS)
		except ValueError, exc:
			pass
		else:
			self.fail("expected a ValueError for invalid address.")

		# Valid group service type and multicast address, ensure it works
		mc_addr = "224.0.0.34"
		service = Service(self._DEF_NAME, group_stype, self._DEF_DOMAIN, mc_addr,
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
		suite.addTest(ServiceTestCase("testGroupService"))
	addToSuite = staticmethod(addToSuite)


def main():
	suite = unittest.TestSuite()
	ServiceTestCase.addToSuite(suite)
	runner = unittest.TextTestRunner()
	runner.run(suite)

if __name__ == "__main__":
	main()
