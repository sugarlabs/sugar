import random

import goocanvas

from view.home.IconLayout import IconLayout
from view.home.MyIcon import MyIcon
from view.FriendIcon import FriendIcon

class FriendsGroup(goocanvas.Group):
	def __init__(self, shell):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._icon_layout = IconLayout(1200, 900)

		me = MyIcon(100)
		me.translate(600 - (me.get_property('size') / 2),
					 450 - (me.get_property('size') / 2))
		self.add_child(me)

		friends = self._shell.get_model().get_friends()

		for friend in friends:
			self.add_friend(friend)

		friends.connect('friend-added', self._friend_added_cb)

	def add_friend(self, friend):
		icon = FriendIcon(self._shell, friend)
		self.add_child(icon)
		self._icon_layout.add_icon(icon)

	def _friend_added_cb(self, data_model, friend):
		self.add_friend(friend)
