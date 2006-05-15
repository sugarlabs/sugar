import xmlrpclib

from sugar.p2p.Service import Service
import network

class RemoteModel:
	def __init__(self, service):
		self._service = service
		
		addr = "http://%s:%d" % (service.get_address(), service.get_port())
		self._client = xmlrpclib.ServerProxy(addr)

	def get_value(self, key):
		return self._client.get_value(key)
		
	def set_value(self, key, value):
		self._client.set_value(key, value)
