from network import *

class StreamReaderRequestHandler(object):
	def __init__(self, reader):
		self._reader = reader

	def message(self, nick_name, message):
		address = network.get_authinfo()
		self._reader.recv(nick_name, message)
		return True

class StreamReader:
	def __init__(self, group, service):
		self._group = group
		self._service = service
		
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
		started = False
		tries = 10
		port = self._service.get_port()
		while not started and tries > 0:
			try:
				p2p_server = GlibXMLRPCServer(("", port))
				p2p_server.register_instance(StreamReaderRequestHandler(self))
				started = True
			except:
				port = port + 1
				tries = tries - 1
		self._service.set_port(port)
		
	def _recv_multicast(self, msg):
		[ nick_name, data ] = msg['data'].split(" |**| ", 2)
		self._recv(nick_name, data)
	
	def _recv(self, nick_name, data):
		if nick_name != self._group.get_owner().get_nick_name():
			self._callback(self._group.get_buddy(nick_name), data)
