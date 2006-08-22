from home.FriendsModel import FriendsModel
from home.MeshModel import MeshModel

class HomeModel:
	def __init__(self):
		self._friends = FriendsModel()
		self._mesh = MeshModel()

	def get_friends(self):
		return self._friends

	def get_mesh(self):
		return self._mesh
