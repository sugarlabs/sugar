import avahi
from sugar import util
import dbus

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
	if not activity_id:
		return name
	if type(name) == type(u""):
		raise ValueError("name must not be in unicode.")
	if not name or type(name) != type(""):
		raise ValueError("name must be a valid string.")
	composed = "%s [%s]" % (name, activity_id)
	return composed.encode()

def _decompose_service_name(name):
	"""Break a service name into the name and activity ID, if we can."""
	if type(name) != type(""):
		raise ValueError("name must be a valid string.")
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
		if type(name) == type(u""):
			name = name.encode()
		stype = sdict['stype']
		if type(stype) == type(u""):
			stype = stype.encode()
		activity_id = sdict['activity_id']
		if type(activity_id) == type(u""):
			activity_id = activity_id.encode()
		domain = sdict['domain']
		if type(domain) == type(u""):
			domain = domain.encode()
		port = sdict['port']
		properties = sdict['properties']
	except KeyError, exc:
		raise ValueError("Serialized service object was not valid.")

	address = None
	try:
		address = sdict['address']
		if type(address) == type(u""):
			address = address.encode()
	except KeyError:
		pass
	name = compose_service_name(name, activity_id)
	return Service(name, stype, domain, address=address,
		port=port, properties=properties)


_ACTIVITY_ID_TAG = "ActivityID"

class Service(object):
	"""Encapsulates information about a specific ZeroConf/mDNS
	service as advertised on the network."""
	def __init__(self, name, stype, domain, address=None, port=-1, properties=None):
		# Validate immutable options
		if name and type(name) == type(u""):
			raise ValueError("name must not be in unicode.")
		if not name or type(name) != type("") or not len(name):
			raise ValueError("must specify a valid service name.")

		if stype and type(stype) == type(u""):
			raise ValueError("service type must not be in unicode.")
		if not stype or type(stype) != type("") or not len(stype):
			raise ValueError("must specify a service type.")
		if not stype.endswith("._tcp") and not stype.endswith("._udp"):
			raise ValueError("must specify a TCP or UDP service type.")

		if domain and type(domain) == type(u""):
			raise ValueError("domain must not be in unicode.")
		if type(domain) != type(""):
			raise ValueError("must specify a domain.")
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

	def serialize(self, owner=None):
		sdict = {}
		if owner is not None:
			sdict['name'] = dbus.Variant(owner.get_nick_name())
		else:
			sdict['name'] = dbus.Variant(self._name)
		sdict['stype'] = dbus.Variant(self._stype)
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
			if type(address) != type("") and type(address) != type(u""):
				raise ValueError("must specify a valid address.")
		if address and type(address) == type(u""):
			address = address.encode()
		self._address = address

	def get_domain(self):
		"""Return the ZeroConf/mDNS domain the service was found in."""
		return self._domain


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
