import random

import goocanvas

from sugar.canvas.IconItem import IconItem
from home.IconLayout import IconLayout
from home.MyIcon import MyIcon
from BuddyPopup import BuddyPopup
from sugar.canvas.Grid import Grid

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

		friends.connect('friend-added', self._friend_added_cb)

	def add_friend(self, friend):
		icon = FriendIcon(friend)

		icon.connect('popup', self._friend_popup_cb)
		icon.connect('popdown', self._friend_popdown_cb)

		self.add_child(icon)
		self._icon_layout.add_icon(icon)

	def _friend_added_cb(self, data_model, friend):
		self.add_friend(friend)

	def _friend_popup_cb(self, icon, x1, y1, x2, y2):
		grid = Grid()

		self._popup = BuddyPopup(self._shell, grid, icon.get_friend())

		[grid_x1, grid_y1] = grid.convert_from_screen(x1, y1)
		[grid_x2, grid_y2] = grid.convert_from_screen(x2, y2)

		if grid_x2 + self._popup.get_width() + 1 > Grid.ROWS:
			grid_x = grid_x1 - self._popup.get_width() + 1
		else:
			grid_x = grid_x2 - 1

		grid_y = grid_y1

		if grid_y < 0:
			grid_y = 0
		if grid_y + self._popup.get_width() > Grid.ROWS:
			grid_y = Grid.ROWS - self._popup.get_width()

		grid.set_constraints(self._popup, grid_x, grid_y,
							 self._popup.get_width(), self._popup.get_height())

		self._popup.show()

	def _friend_popdown_cb(self, friend):
		self._popup.popdown()
		self._popup = None
