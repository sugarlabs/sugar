import presence

class Service(object):
	def __init__(self, name, stype, address, port, multicast=False):
		self._name = name
		self._stype = stype
		self._address = str(address)
		self._port = int(port)
		self._multicast = multicast

	def get_name(self):
		return self._name
	
	def get_type(self):
		return self._stype

	def get_address(self):
		return self._address

	def get_port(self):
		return self._port
		
	def is_multicast(self):
		return self._multicast
	
	def register(self, group):	
		pannounce = presence.PresenceAnnounce()
		pannounce.register_service(self._name, self._port, self._stype)
