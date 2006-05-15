import presence

class Service(object):
	def __init__(self, name, stype, port, group_address = None):
		self._name = name
		self._stype = stype
		self._port = int(port)
		self._address = ''
		self._group_address = group_address

	def get_name(self):
		return self._name
	
	def get_type(self):
		return self._stype

	def get_port(self):
		return self._port

	def set_port(self, port):
		self._port = port

	def get_address(self):
		return self._address

	def get_group_address(self):
		return self._group_address

	def set_address(self, address):
		self._address = address

	def set_group_address(self):
		self._group_address = group_address

	def is_multicast(self):
		return self._group_address != None
	
	def register(self, group):	
		pannounce = presence.PresenceAnnounce()
		if self._group_address:
			pannounce.register_service(self._name, self._port, self._stype,
									   group_address = self._group_address)
		else:
			pannounce.register_service(self._name, self._port, self._stype)
