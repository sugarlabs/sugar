from home.FriendsModel import FriendsModel

class HomeModel:
	def __init__(self):
		self._friends = FriendsModel()

	def get_friends(self):
		return self._friends
