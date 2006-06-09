import avahi

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

		if not domain or (type(domain) != type("") and type(domain) != type(u"")):
			raise ValueError("must specify a domain.")
		if domain != "local" and domain != u"local":
			raise ValueError("must use the 'local' domain (for now).")

		self._name = name
		self._stype = stype
		self._domain = domain
		self._address = None
		self.set_address(address)
		self._port = -1
		self.set_port(port)
		self._properties = {}
		self.set_properties(properties)

	def get_name(self):
		return self._name

	def get_one_property(self, key):
		if key in self._properties.keys():
			return self._properties[key]
		return None

	def get_properties(self):
		return self._properties

	def set_properties(self, properties):
		self._properties = {}
		if type(properties) == type([]):
			self._properties = _txt_to_dict(properties)
		elif type(properties) == type({}):
			self._properties = properties

	def get_type(self):
		return self._stype

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
		return self._domain

	def is_olpc_service(self):
		if self._stype.endswith("._olpc._udp") or self._stype.endswith(".olpc._tcp"):
			return True
		return False


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

	def addToSuite(suite):
		suite.addTest(ServiceTestCase("testName"))
		suite.addTest(ServiceTestCase("testType"))
		suite.addTest(ServiceTestCase("testDomain"))
		suite.addTest(ServiceTestCase("testAddress"))
		suite.addTest(ServiceTestCase("testPort"))
		suite.addTest(ServiceTestCase("testGoodInit"))
		suite.addTest(ServiceTestCase("testAvahiProperties"))
		suite.addTest(ServiceTestCase("testBoolProperty"))
	addToSuite = staticmethod(addToSuite)


def main():
	suite = unittest.TestSuite()
	ServiceTestCase.addToSuite(suite)
	runner = unittest.TextTestRunner()
	runner.run(suite)

if __name__ == "__main__":
	main()
