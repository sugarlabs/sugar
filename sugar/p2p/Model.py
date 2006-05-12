MODEL_SERVICE_TYPE = "_olpc_model._tcp"
MODEL_SERVICE_PORT = 6300

class RemoteModel:
	def __init__(self, service):
		self._service = service
		
		addr = "http://%s:%d" % (service.get_address(), service.get_port())
		self._client = xmlrpclib.ServerProxy(addr)

	def get_value(self, key):
		self._client.get_value(key)
		
	def set_value(self, key, value):
		self._client.set_value(key, value)

class ModelRequestHandler(object):
	def __init__(self, model):
		self._model = model

	def get_value(self, key):
		return self._model.get_value(key)

	def set_value(self, key, value):
		return self._model.set_value(key, value)

class LocalModel:
	def __init__(self, group, model_id):
		self._group = group
		self._model_id = model_id
		self._values = {}
	
	def get_value(self, key):
		return self._values[key]
		
	def set_value(self, key, value):
		self._values[key] = value

	def _setup_service(self):
		service = Service(self._model_id, MODEL_SERVICE_TYPE,
						  '', MODEL_SERVICE_PORT)
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
				p2p_server.register_instance(StreamReaderRequestHandler(self))
				started = True
			except:
				port = port + 1
				tries = tries - 1
		service.set_port(port)
		
class Store:
	def __init__(self, group):
		self._group = group
		self._local_models = {}
	
	def create_model(self, model_id):
		model = LocalModel(self._group, model_id)
		self._local_models[model_id] = model
		return model
	
	def get_model(self, model_id):
		if self._local_models.has_key(model_id):
			return self._local_models(model_id)
		else:
			service = self._group.get_service(model_id, MODEL_SERVICE_TYPE)
			if service:
				return RemoteModel(service)
			else:
				return None
