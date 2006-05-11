from network import *

class StreamReaderRequestHandler(object):
	def __init__(self, reader):
		self._reader = reader

	def message(self, message):
		address = network.get_authinfo()
		self._reader.recv(address[0], message)
		return True

class StreamReader:
	def __init__(self, group, service_name):
		self._group = group
		self._service_name = service_name
		
		self._service = group.get_service_from_name(service_name)
		if self._service.is_multicast():
			self._setup_multicast()
		else:
			self._setup_unicast()

	def set_listener(self, callback):
		self._callback = callback

	def _setup_multicast(self):
		address = self._service.get_address()
		port = self._service.get_port()
		server = GroupServer(address, port, self._recv_multicast)
		server.start()
		
	def _setup_unicast(self):
		p2p_server = GlibXMLRPCServer(("", self._service.get_port()))
		p2p_server.register_instance(StreamReaderRequestHandler(self))
		
	def _recv_multicast(self, msg):
		self._recv(msg['addr'], msg['data'])
	
	def _recv(self, address, data):
		buddy = self._group.get_buddy_from_address(address)
		self._callback(buddy, data)
