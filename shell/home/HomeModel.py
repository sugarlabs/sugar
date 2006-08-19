from home.FriendsModel import FriendsModel
from home.MeshModel import MeshModel

class HomeModel:
	def __init__(self, registry):
		self._friends = FriendsModel()
		self._mesh = MeshModel(registry)

	def get_friends(self):
		return self._friends

	def get_mesh(self):
		return self._mesh
