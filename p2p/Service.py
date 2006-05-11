class Service(object):
	def __init__(self, name, host, address, port, multicast=False):
		self._name = name
		self._host = host
		self._address = str(address)
		self._port = int(port)
		self._multicast = multicast

	def get_name(self):
		return self._name

	def get_host(self):
		return self._host

	def get_address(self):
		return self._address

	def get_port(self):
		return self._port
		
	def is_multicast(self):
		return self._multicast
