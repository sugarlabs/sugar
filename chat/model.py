import p2p

class ModelListener:
	def __init__(self):
		pass
	
	def model_changed(self, key, value):
		pass

class Model:
	def __init__(self):
		creator = Owner.getInstance()
		self._uri = "urn:model:" + creator.get_id() + ":" + random()
		self._values = {}
		self.__listeners = []

	def get_value(self, key):
		return self._values[key]
		
	def set_value(self, key, value):
		self._values[key] = value
		notify_changed(key, value)
		
	def add_listener(self, listener):
		self.__listeners.add(listener)
		
	def notify_changed(self, key, value):
		for listener in self.__listeners:
			listener.model_changed(key, value)

	def serialize(model):
		return [ self._uri, self._values ]
	
	serialize = staticmethod(serialize)

	def deserialize(data):
		[uri, values] = data

		# FIXME How damn I do this right in python?
		model = Model()
		model._uri = uri
		model._values = values

		return model
	
	deserialize = staticmethod(deserialize)

class ModelChangeSet:
	def __init__(self):
		self._values = {}
		
	def add(self, key, value):
		self._values[key] = value

class ClientModelListener(ModelListener):
	def __init__(self, client, model):
		self._model = model
	
	def model_changed(self, key, value):
		client.add_change(self._model, key, value)

class ModelStore:
	instance = None
	
	def __init__(self):
		self._models = {}
		self._group = p2p.Group.get_instance()

		input_pipe = p2p.InputPipe(self._group, "model-store")
		input_pipe.listen(self._model_request)
	
	def get_instance():
		if not ModelStore.instance:
			ModelStore.instance = ModelStore()
		return ModelStore.instance
		
	get_instance = staticmethod(get_instance)

	def add_model(self, model):
		self._models[model.get_id(), model]

	def _model_request(self, buddy, msg):
		parts = msg.split(':')
		model_id = self._group.get_buddy(parts[3])
		model = self._models[model_id]
		return model.serialize()

class ModelContext:
	def __init__(self):
		self._store = ModelStore.get_instance()
		self._changes = {}
	
	def _add_model(self, model):
		self._store.add_model(model)
		
		change_set = ModelChangeSet()
		self.__changes[model_id, change_set]
		
		listener = ClientModelListener(self)
		model.add_listener(listener)
	
	def fetch(self, model_uri):
		parts = model_uri.split(':')
		buddy = Group.get_instance().get_buddy(parts[2])

		output_pipe = p2p.OutputPipe(group, buddy, "model-store")
		model = output_pipe.send(model_uri)

		self._add_model(model)
		
	def commit(self):
		pass
	
	def add_change(self, model, key, value):
		change_set = self.__changes[model.get_id()]
		change_set.add(key, value)
