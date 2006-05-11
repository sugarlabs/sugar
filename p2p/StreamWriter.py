import socket

import network

class StreamWriter:
	def __init__(self, group, service_name):
		self._group = group
		self._service_name = service_name
		self._service = group.get_service_from_name(service_name)
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
			self._uclient.message(data)
			return True
		except (socket.error, xmlrpclib.Fault, xmlrpclib.ProtocolError), e:
			traceback.print_exc()
			return False

	def _setup_multicast(self):
		self._mclient = network.GroupClient(self._address, self._port)
		
	def _multicast_write(self, data):
		self._mclient.send_msg(data)
