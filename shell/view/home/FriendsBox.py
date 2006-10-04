import random

import hippo

from sugar.graphics.spreadlayout import SpreadLayout
from view.home.MyIcon import MyIcon
from view.BuddyActivityView import BuddyActivityView

class FriendsBox(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarFriendsBox'
	def __init__(self, shell, menu_shell):
		hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff)

		self._shell = shell
		self._menu_shell = menu_shell
		self._layout = SpreadLayout()
		self._friends = {}

		self._my_icon = MyIcon(112)
		self.append(self._my_icon, hippo.PACK_FIXED)

		friends = self._shell.get_model().get_friends()

		for friend in friends:
			self.add_friend(friend)

		friends.connect('friend-added', self._friend_added_cb)
		friends.connect('friend-removed', self._friend_removed_cb)

	def add_friend(self, buddy_info):
		icon = BuddyActivityView(self._shell, self._menu_shell, buddy_info)
		self.append(icon, hippo.PACK_FIXED)

		self._friends[buddy_info.get_name()] = icon

	def _friend_added_cb(self, data_model, buddy_info):
		self.add_friend(buddy_info)

	def _friend_removed_cb(self, data_model, name):
		self.remove(self._friends[name])
		del self._friends[name]

	def do_allocate(self, width, height):
		hippo.CanvasBox.do_allocate(self, width, height)

		self._layout.layout(self)

		[icon_width, icon_height] = self._my_icon.get_allocation()
		self.move(self._my_icon, (width - icon_width) / 2,
				  (height - icon_height) / 2)
