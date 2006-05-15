class AbstractModel:
	def __init__(self):
		self._listeners = []
	
	def add_listener(self, listener):
		self._listeners.append(listener)
	
	def _notify_model_change(self, key):
		for listener in self._listeners:
			listener(self, key)
