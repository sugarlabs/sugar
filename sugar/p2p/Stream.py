import xmlrpclib
import socket
import traceback
import random

import network
from MostlyReliablePipe import MostlyReliablePipe
from sugar.presence import Service

class Stream(object):
	def __init__(self, service):
		if not isinstance(service, Service.Service):
			raise ValueError("service must be valid.")
		if not service.get_port():
			raise ValueError("service must have an address.")
		self._service = service
		self._reader_port = self._service.get_port()
		self._writer_port = self._reader_port
		self._address = self._service.get_address()
		self._callback = None

	def new_from_service(service, start_reader=True):
		if not isinstance(service, Service.Service):
			raise ValueError("service must be valid.")
		if service.is_multicast_service():
			return MulticastStream(service)
		else:
			return UnicastStream(service, start_reader)
	new_from_service = staticmethod(new_from_service)

	def set_data_listener(self, callback):
		self._callback = callback

	def _recv(self, address, data):
		if self._callback:
			self._callback(data)


class UnicastStreamWriter(object):
	def __init__(self, stream, service):
		# set up the writer
		if not isinstance(service, Service.Service):
			raise ValueError("service must be valid")
		self._service = service
		if not service.get_address():
			raise ValueError("service must have a valid address.")
		self._address = self._service.get_address()
		self._port = self._service.get_port()
		self._xmlrpc_addr = "http://%s:%d" % (self._address, self._port)
		self._writer = network.GlibServerProxy(self._xmlrpc_addr)

	def write(self, xmlrpc_data):
		"""Write some data to the default endpoint of this pipe on the remote server."""
		try:
			self._writer.message(None, None, xmlrpc_data)
			return True
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError):
			traceback.print_exc()
		return False

	def custom_request(self, method_name, request_cb, user_data, *args):
		"""Call a custom XML-RPC method on the remote server."""
		try:
			method = getattr(self._writer, method_name)
			method(request_cb, user_data, *args)
			return True
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError):
			traceback.print_exc()
		return False


class UnicastStream(Stream):
	def __init__(self, service, start_reader=True):
		"""Initializes the stream.  If the 'start_reader' argument is True,
		the stream will initialize and start a new stream reader, if it
		is False, no reader will be created and the caller must call the
		start_reader() method to start the stream reader and be able to
		receive any data from the stream."""
		Stream.__init__(self, service)
		if start_reader:
			self.start_reader()

	def start_reader(self, update_service_port=True):
		"""Start the stream's reader, which for UnicastStream objects is
		and XMLRPC server.  If there's a port conflict with some other
		service, the reader will try to find another port to use instead.
		Returns the port number used for the reader."""
		# Set up the reader
		started = False
		tries = 10
		self._reader = None
		while not started and tries > 0:
			try:
				self._reader = network.GlibXMLRPCServer(("", self._reader_port))
				self._reader.register_function(self._message, "message")
				if update_service_port:
					self._service.set_port(self._reader_port)  # Update the service's port
				started = True
			except(socket.error):
				self._reader_port = random.randint(self._reader_port + 1, 65500)
				tries = tries - 1
		if self._reader is None:
			print 'Could not start stream reader.'
		return self._reader_port

	def _message(self, message):
		"""Called by the XMLRPC server when network data arrives."""
		address = network.get_authinfo()
		self._recv(address, message)
		return True

	def register_reader_handler(self, handler, name):
		"""Register a custom message handler with the reader.  This call
		adds a custom XMLRPC method call with the name 'name' to the reader's
		XMLRPC server, which then calls the 'handler' argument back when
		a method call for it arrives over the network."""
		if name == "message":
			raise ValueError("Handler name 'message' is a reserved handler.")
		self._reader.register_function(handler, name)

	def new_writer(self, service):
		"""Return a new stream writer object."""
		return UnicastStreamWriter(self, service)


class MulticastStream(Stream):
	def __init__(self, service):
		Stream.__init__(self, service)
		self._service = service
		self._internal_start_reader()

	def start_reader(self):
		return self._reader_port

	def _internal_start_reader(self):
		if not self._service.get_address():
			raise ValueError("service must have a valid address.")
		self._pipe = MostlyReliablePipe('', self._address, self._reader_port,
				self._recv_data_cb)
		self._pipe.start()

	def write(self, data):
		self._pipe.send(data)

	def _recv_data_cb(self, address, data, user_data=None):
		self._recv(address, data)

	def new_writer(self, service=None):
		return self
