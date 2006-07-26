import socket
import logging

from sugar.p2p.Notifier import Notifier
from sugar.p2p.model.AbstractModel import AbstractModel
from sugar.p2p import network

class ModelRequestHandler(object):
	def __init__(self, model):
		self._model = model

	def get_value(self, key):
		return self._model.get_value(key)

	def set_value(self, key, value):
		return self._model.set_value(key, value)

class LocalModel(AbstractModel):
	SERVICE_TYPE = "_olpc_model._tcp"

	def __init__(self, activity, pservice, service):
		AbstractModel.__init__(self)
		self._pservice = pservice
		self._activity = activity
		self._service = service
		self._values = {}
		
		self._setup_service()
		self._notifier = Notifier(service)
	
	def get_value(self, key):
		return self._values[key]
		
	def set_value(self, key, value):
		self._values[key] = value
		self._notify_model_change(key)
		self._notifier.notify(key)

	def _setup_service(self):
		service = self._pservice.share_activity(self._activity,
				stype = LocalModel.SERVICE_TYPE,
				address = '')
		self._setup_server(service)
	
	# FIXME this is duplicated with StreamReader
	def _setup_server(self, service):
		port = service.get_port()
		logging.debug('Start model server on port %d' % (port))
		p2p_server = network.GlibXMLRPCServer(("", port))
		p2p_server.register_instance(ModelRequestHandler(self))
