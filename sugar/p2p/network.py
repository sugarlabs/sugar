# -*- tab-width: 4; indent-tabs-mode: t -*- 

import socket
import threading
import traceback
import select
import time
import xmlrpclib
import sys

import gobject
import SimpleXMLRPCServer
import SocketServer

__authinfos = {}

def _add_authinfo(authinfo):
	__authinfos[threading.currentThread()] = authinfo

def get_authinfo():
	return __authinfos.get(threading.currentThread())

def _del_authinfo():
	del __authinfos[threading.currentThread()]


class GlibTCPServer(SocketServer.TCPServer):
	"""GlibTCPServer

	Integrate socket accept into glib mainloop.
	"""

	allow_reuse_address = True
	request_queue_size = 20

	def __init__(self, server_address, RequestHandlerClass):
		SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
		self.socket.setblocking(0)  # Set nonblocking

		# Watch the listener socket for data
		gobject.io_add_watch(self.socket, gobject.IO_IN, self._handle_accept)

	def _handle_accept(self, source, condition):
		if not (condition & gobject.IO_IN):
			return True
		self.handle_request()
		return True

class GlibXMLRPCRequestHandler(SimpleXMLRPCServer.SimpleXMLRPCRequestHandler):
	""" GlibXMLRPCRequestHandler
	
	The stock SimpleXMLRPCRequestHandler and server don't allow any way to pass
	the client's address and/or SSL certificate into the function that actually
	_processes_ the request.  So we have to store it in a thread-indexed dict.
	"""

	def do_POST(self):
		_add_authinfo(self.client_address)
		try:
			SimpleXMLRPCServer.SimpleXMLRPCRequestHandler.do_POST(self)
		except socket.timeout:
			pass
		except socket.error, e:
			print "Error (%s): socket error - '%s'" % (self.client_address, e)
		except:
			print "Error while processing POST:"
			traceback.print_exc()
		_del_authinfo()

class GlibXMLRPCServer(GlibTCPServer, SimpleXMLRPCServer.SimpleXMLRPCDispatcher):
	"""GlibXMLRPCServer
	
	Use nonblocking sockets and handle the accept via glib rather than
	blocking on accept().
	"""

	def __init__(self, addr, requestHandler=GlibXMLRPCRequestHandler, logRequests=1):
		self.logRequests = logRequests

		SimpleXMLRPCServer.SimpleXMLRPCDispatcher.__init__(self)
		GlibTCPServer.__init__(self, addr, requestHandler)

	def _marshaled_dispatch(self, data, dispatch_method = None):
		"""Dispatches an XML-RPC method from marshalled (XML) data.

		XML-RPC methods are dispatched from the marshalled (XML) data
		using the _dispatch method and the result is returned as
		marshalled data. For backwards compatibility, a dispatch
		function can be provided as an argument (see comment in
		SimpleXMLRPCRequestHandler.do_POST) but overriding the
		existing method through subclassing is the prefered means
		of changing method dispatch behavior.
		"""

		params, method = xmlrpclib.loads(data)

		# generate response
		try:
			if dispatch_method is not None:
				response = dispatch_method(method, params)
			else:
				response = self._dispatch(method, params)
			# wrap response in a singleton tuple
			response = (response,)
			response = xmlrpclib.dumps(response, methodresponse=1)
		except xmlrpclib.Fault, fault:
			response = xmlrpclib.dumps(fault)
		except:
			print "Exception while processing request:"
			traceback.print_exc()

			# report exception back to server
			response = xmlrpclib.dumps(
				xmlrpclib.Fault(1, "%s:%s" % (sys.exc_type, sys.exc_value))
				)

		return response

class GroupServer(object):

	_MAX_MSG_SIZE = 500

	def __init__(self, address, port, data_cb):
		self._address = address
		self._port = port
		self._data_cb = data_cb

		self._setup_listener()

	def _setup_listener(self):
		# Listener socket
		self._listen_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

		# Set some options to make it multicast-friendly
		self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		try:
			self._listen_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
		except:
			pass
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)

	def start(self):
		# Set some more multicast options
		self._listen_sock.bind(('', self._port))
		self._listen_sock.settimeout(2)
		intf = socket.gethostbyname(socket.gethostname())
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF, socket.inet_aton(intf) + socket.inet_aton('0.0.0.0'))
		self._listen_sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP, socket.inet_aton(self._address) + socket.inet_aton('0.0.0.0'))

		# Watch the listener socket for data
		gobject.io_add_watch(self._listen_sock, gobject.IO_IN, self._handle_incoming_data)

	def _handle_incoming_data(self, source, condition):
		if not (condition & gobject.IO_IN):
			return True
		msg = {}
		msg['data'], (msg['addr'], msg['port']) = source.recvfrom(self._MAX_MSG_SIZE)
		if self._data_cb:
			self._data_cb(msg)
		return True

class GroupClient(object):

	_MAX_MSG_SIZE = 500

	def __init__(self, address, port):
		self._address = address
		self._port = port

		self._send_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		# Make the socket multicast-aware, and set TTL.
		self._send_sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 20) # Change TTL (=20) to suit

	def send_msg(self, data):
		self._send_sock.sendto(data, (self._address, self._port))
