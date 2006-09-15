import random

import goocanvas

from home.IconLayout import IconLayout
from home.MyIcon import MyIcon
from FriendIcon import FriendIcon

class FriendsGroup(goocanvas.Group):
	def __init__(self, shell_model):
		goocanvas.Group.__init__(self)

		self._shell_model = shell_model
		self._icon_layout = IconLayout(1200, 900)
		self._friends = shell_model.get_friends()

		me = MyIcon(100)
		me.translate(600 - (me.get_property('size') / 2),
					 450 - (me.get_property('size') / 2))
		self.add_child(me)

		for friend in self._friends:
			self.add_friend(friend)

		self._friends.connect('friend-added', self._friend_added_cb)

	def add_friend(self, friend):
		icon = FriendIcon(self._shell_model, friend)
		self.add_child(icon)
		self._icon_layout.add_icon(icon)

	def _friend_added_cb(self, data_model, friend):
		self.add_friend(friend)
