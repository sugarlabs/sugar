import random

import goocanvas

from sugar.canvas.IconItem import IconItem
from home.IconLayout import IconLayout
from home.MyIcon import MyIcon

class FriendIcon(IconItem):
	def __init__(self, friend):
		IconItem.__init__(self, icon_name='stock-buddy',
						  color=friend.get_color(), size=96)
		self._friend = friend

	def get_friend(self):
		return self._friend

class FriendsGroup(goocanvas.Group):
	def __init__(self, shell, friends):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._icon_layout = IconLayout(1200, 900)
		self._friends = friends

		me = MyIcon(100)
		me.translate(600 - (me.get_property('size') / 2),
					 450 - (me.get_property('size') / 2))
		self.add_child(me)

		for friend in self._friends:
			self.add_friend(friend)

		friends.connect('friend-added', self.__friend_added_cb)

	def __friend_clicked_cb(self, icon):
		activity = self._shell.get_current_activity()
		buddy = icon.get_friend().get_buddy()
		if buddy != None:
			activity.invite(buddy)

	def add_friend(self, friend):
		icon = FriendIcon(friend)
		icon.connect('clicked', self.__friend_clicked_cb)
		self.add_child(icon)
		self._icon_layout.add_icon(icon)

	def __friend_added_cb(self, data_model, friend):
		self.add_friend(friend)
