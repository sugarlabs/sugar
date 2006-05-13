import xmlrpclib
import traceback
import socket

import network

class StreamWriter:
	def __init__(self, group, service):
		self._group = group
		self._service = service
		self._address = self._service.get_address()
		self._port = self._service.get_port()

		if self._service.is_multicast():
			self._setup_multicast()
		else:
			self._setup_unicast()
		
	def write(self, data):
		if self._service.is_multicast():
			self._multicast_write(data)
		else:
			self._unicast_write(data)

	def _setup_unicast(self):
		xmlrpc_addr = "http://%s:%d" % (self._address, self._port)
		self._uclient = xmlrpclib.ServerProxy(xmlrpc_addr)

	def _unicast_write(self, data):
		try:
			nick_name = self._group.get_owner().get_nick_name()
			self._uclient.message(nick_name, data)
			return True
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError):
			traceback.print_exc()
			return False

	def _setup_multicast(self):
		self._mclient = network.GroupClient(self._address, self._port)
		
	def _multicast_write(self, data):
		nick_name = self._group.get_owner().get_nick_name()
		self._mclient.send_msg(nick_name + " |**| " + data)
