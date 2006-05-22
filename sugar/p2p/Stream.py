import xmlrpclib
import socket
import traceback
import threading

import pygtk
pygtk.require('2.0')
import gobject


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


class UnicastStreamWriterBase(object):
	def __init__(self, stream, service, owner_nick_name):
		# set up the writer
		if not service:
			raise ValueError("service must be valid")
		self._service = service
		self._owner_nick_name = owner_nick_name
		self._address = self._service.get_address()
		self._port = self._service.get_port()
		self._xmlrpc_addr = "http://%s:%d" % (self._address, self._port)

class UnicastStreamWriter(UnicastStreamWriterBase):
	def __init__(self, stream, service, owner_nick_name):
		UnicastStreamWriterBase.__init__(self, stream, service, owner_nick_name)
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
			pass
			#traceback.print_exc()
		return None


class ThreadedRequest(threading.Thread):
	def __init__(self, controller, addr, method, response_cb, user_data, *args):
		threading.Thread.__init__(self)
		self._controller = controller
		self._method = method
		self._args = args
		self._response_cb = response_cb
		self._user_data = user_data
		self._writer = xmlrpclib.ServerProxy(addr)

	def run(self):
		response = None
		try:
			method = getattr(self._writer, self._method)
			response = method(*self._args)
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError):
			traceback.print_exc()
		if self._response_cb:
			gobject.idle_add(self._response_cb, response, self._user_data)
		self._controller.notify_request_done(self)

class ThreadedUnicastStreamWriter(UnicastStreamWriterBase):
	def __init__(self, stream, service, owner_nick_name):
		self._requests_lock = threading.Lock()
		self._requests = []
		UnicastStreamWriterBase.__init__(self, stream, service, owner_nick_name)

	def _add_request(self, request):
		self._requests_lock.acquire()
		if not request in self._requests:
			self._requests.append(request)
		self._requests_lock.release()

	def write(self, response_cb, user_data, data):
		"""Write some data to the default endpoint of this pipe on the remote server."""
		request = ThreadedRequest(self, self._xmlrpc_addr, "message", response_cb,
				user_data, self._owner_nick_name, data)
		self._add_request(request)
		request.start()

	def custom_request(self, method_name, response_cb, user_data, *args):
		"""Call a custom XML-RPC method on the remote server."""
		request = ThreadedRequest(self, self._xmlrpc_addr, method_name, response_cb,
				user_data, *args)
		self._add_request(request)
		request.start()

	def notify_request_done(self, request):
		self._requests_lock.acquire()
		if request in self._requests:
			self._requests.remove(request)
		self._requests_lock.release()


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

	def new_writer(self, service, threaded=False):
		if threaded:
			return ThreadedUnicastStreamWriter(self, service, self._owner_nick_name)
		else:
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

	def new_writer(self, service=None, threaded=False):
		return self
