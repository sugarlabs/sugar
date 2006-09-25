import random

import goocanvas

from view.home.IconLayout import IconLayout
from view.home.MyIcon import MyIcon
from view.BuddyIcon import BuddyIcon

class FriendsGroup(goocanvas.Group):
	def __init__(self, shell, menu_shell):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._menu_shell = menu_shell
		self._icon_layout = IconLayout(shell.get_grid())
		self._friends = {}

		me = MyIcon(112)
		me.translate(600 - (me.get_property('size') / 2),
					 450 - (me.get_property('size') / 2))
		self.add_child(me)

		friends = self._shell.get_model().get_friends()

		for friend in friends:
			self.add_friend(friend)

		friends.connect('friend-added', self._friend_added_cb)
		friends.connect('friend-removed', self._friend_removed_cb)

	def add_friend(self, buddy_info):
		icon = BuddyIcon(self._shell, self._menu_shell, buddy_info)
		self.add_child(icon)
		self._icon_layout.add_icon(icon)

		self._friends[buddy_info.get_name()] = icon

	def _friend_added_cb(self, data_model, buddy_info):
		self.add_friend(buddy_info)

	def _friend_removed_cb(self, data_model, name):
		self.remove_child(self._friends[name])
		del self._friends[name]
