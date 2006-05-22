import xmlrpclib
import socket
import traceback

import network
from MostlyReliablePipe import MostlyReliablePipe

class Stream(object):
	def __init__(self, service, group):
		if not service:
			raise ValueError("service must be valid")
		self._service = service
		self._group = group
		self._owner_nick_name = self._group.get_owner().get_nick_name()
		self._port = self._service.get_port()
		self._address = self._service.get_address()
		self._callback = None

	def new_from_service(service, group):
		if service.is_multicast():
			return MulticastStream(service, group)
		else:
			return UnicastStream(service, group)
	new_from_service = staticmethod(new_from_service)

	def set_data_listener(self, callback):
		self._callback = callback

	def recv(self, nick_name, data):
		if nick_name != self._owner_nick_name:
			if self._callback:
				self._callback(self._group.get_buddy(nick_name), data)


class UnicastStreamWriter(object):
	def __init__(self, stream, service, owner_nick_name):
		# set up the writer
		if not service:
			raise ValueError("service must be valid")
		self._service = service
		self._owner_nick_name = owner_nick_name
		self._address = self._service.get_address()
		self._port = self._service.get_port()
		self._xmlrpc_addr = "http://%s:%d" % (self._address, self._port)
		self._writer = xmlrpclib.ServerProxy(self._xmlrpc_addr)

	def write(self, data):
		"""Write some data to the default endpoint of this pipe on the remote server."""
		try:
			self._writer.message(self._owner_nick_name, data)
			return True
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError):
			traceback.print_exc()
		return False

	def custom_request(self, method_name, *args):
		"""Call a custom XML-RPC method on the remote server."""
		try:
			method = getattr(self._writer, method_name)
			return method(*args)
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError):
			traceback.print_exc()
		return None


class UnicastStream(Stream):
	def __init__(self, service, group):
		Stream.__init__(self, service, group)
		self._setup()

	def _setup(self):
		# Set up the reader
		started = False
		tries = 10
		port = self._service.get_port()
		self._reader = None
		while not started and tries > 0:
			try:
				self._reader = network.GlibXMLRPCServer(("", port))
				self._reader.register_function(self._message, "message")
				started = True
			except(socket.error):
				port = port + 1
				tries = tries - 1
		self._service.set_port(port)

	def _message(self, nick_name, message):
		"""Called by the XMLRPC server when network data arrives."""
		self.recv(nick_name, message)
		return True

	def register_handler(self, handler, name):
		if name == "message":
			raise ValueError("Handler name 'message' is a reserved handler.")
		self._reader.register_function(handler, name)

	def new_writer(self, service):
		return UnicastStreamWriter(self, service, self._owner_nick_name)


class MulticastStream(Stream):
	def __init__(self, service, group):
		Stream.__init__(self, service, group)
		self._address = self._service.get_group_address()
		self._setup()

	def _setup(self):
		self._pipe = MostlyReliablePipe('', self._address, self._port, self._recv_data_cb)
		self._pipe.start()

	def write(self, data):
		self._pipe.send(self._owner_nick_name + " |**| " + data)

	def _recv_data_cb(self, addr, data, user_data=None):
		[ nick_name, data ] = data.split(" |**| ", 2)
		self.recv(nick_name, data)

	def new_writer(self, service=None):
		return self
