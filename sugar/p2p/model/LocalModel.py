import socket

from sugar.p2p.Service import Service
from sugar.p2p.model.AbstractModel import AbstractModel
import network

class ModelRequestHandler(object):
	def __init__(self, model):
		self._model = model

	def get_value(self, key):
		return self._model.get_value(key)

	def set_value(self, key, value):
		return self._model.set_value(key, value)

class LocalModel(AbstractModel):
	SERVICE_TYPE = "_olpc_model._tcp"
	SERVICE_PORT = 6300

	def __init__(self, group, model_id):
		AbstractModel.__init__(self)
		self._group = group
		self._model_id = model_id
		self._values = {}
		
		self._setup_service()
		self._setup_notification()
	
	def get_value(self, key):
		return self._values[key]
		
	def set_value(self, key, value):
		self._values[key] = value
		self._notify_model_change(key)

	def _setup_service(self):
		service = Service(self._model_id, LocalModel.SERVICE_TYPE, '',
						  LocalModel.SERVICE_PORT)
		self._setup_server(service)
		service.register(self._group)
	
	# FIXME this is duplicated with StreamReader
	def _setup_server(self, service):
		started = False
		tries = 10
		port = service.get_port()
		while not started and tries > 0:
			try:
				p2p_server = network.GlibXMLRPCServer(("", port))
				p2p_server.register_instance(ModelRequestHandler(self))
				started = True
			except(socket.error):
				port = port + 1
				tries = tries - 1
		service.set_port(port)
