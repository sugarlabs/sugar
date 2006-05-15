import presence

class Service(object):
	def __init__(self, name, stype, port, mgroup=None):
		self._name = name
		self._stype = stype
		self._port = int(port)
		self._mgroup = mgroup

	def get_name(self):
		return self._name
	
	def get_type(self):
		return self._stype

	def get_address(self):
		return self._address

	def get_port(self):
		return self._port

	def set_port(self, port):
		self._port = port
		
	def get_multicast_group(self):
		return self._mgroup
		
	def is_multicast(self):
		return self._mgroup != None
	
	def register(self, group):	
		pannounce = presence.PresenceAnnounce()
		if self._mgroup:
			pannounce.register_service(self._name, self._port, self._stype,
									   multicast = self._mgroup)
		else:
			pannounce.register_service(self._name, self._port, self._stype)
