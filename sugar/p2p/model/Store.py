from sugar.p2p.model.RemoteModel import RemoteModel
from sugar.p2p.model.LocalModel import LocalModel

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
			return self._local_models[model_id]
		else:
			service = self._group.get_service(model_id, LocalModel.SERVICE_TYPE)
			if service:
				return RemoteModel(self._group, service)
			else:
				return None
