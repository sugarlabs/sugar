import random

import goocanvas

from sugar.canvas.IconItem import IconItem
import Theme

class FriendIcon(IconItem):
	def __init__(self, friend):
		IconItem.__init__(self, icon_name='stock-buddy',
						  color=friend.get_color(), size=96)
		self._friend = friend

	def get_friend(self):
		return self._friend

class FriendsGroup(goocanvas.Group):
	WIDTH = 1200.0 * 1.9
	HEIGHT = 900.0 * 1.9

	def __init__(self, friends, icon_layout):
		goocanvas.Group.__init__(self)

		self._icon_layout = icon_layout
		self._friends = friends

		self._theme = Theme.get_instance()
		self._theme.connect("theme-changed", self.__theme_changed_cb)

		color = self._theme.get_home_friends_color()
		self._friends_rect = goocanvas.Rect(width=FriendsGroup.WIDTH,
											height=FriendsGroup.HEIGHT,
											line_width=0, fill_color=color,
											radius_x=60, radius_y=60)
		self.add_child(self._friends_rect)

		for friend in self._friends:
			self.add_friend(friend)

		friends.connect('friend-added', self.__friend_added_cb)

	def __theme_changed_cb(self, theme):
		color = self._theme.get_home_friends_color()
		self._friends_rect.set_property("fill-color", color)

	def add_friend(self, friend):
		icon = FriendIcon(friend)
		self.add_child(icon)
		self._icon_layout.add_icon(icon)

	def __friend_added_cb(self, data_model, friend):
		self.add_friend(friend)
