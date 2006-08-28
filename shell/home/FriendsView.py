import random

import goocanvas

from sugar.canvas.IconItem import IconItem
import Theme

class FriendIcon(IconItem):
	def __init__(self, friend):
		IconItem.__init__(self, icon_name='stock-buddy',
						  color=friend.get_color(), size=48,
						  x=random.random() * 1100,
						  y=random.random() * 800)
		self._friend = friend

	def get_friend(self):
		return self._friend

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, data_model):
		goocanvas.CanvasModelSimple.__init__(self)
		self._friend_to_child = {}

		self._theme = Theme.get_instance()
		self._theme.connect("theme-changed", self.__theme_changed_cb)

		self._root = self.get_root_item()

		color = self._theme.get_home_mesh_color()
		self._mesh_rect = goocanvas.Rect(width=1200, height=900,
										 fill_color=color)
		self._root.add_child(self._mesh_rect)

		color = self._theme.get_home_friends_color()
		self._friends_rect = goocanvas.Rect(x=100, y=100, width=1000, height=700,
											line_width=0, fill_color=color,
											radius_x=30, radius_y=30)
		self._root.add_child(self._friends_rect)

		color = self._theme.get_home_activities_color()
		self._home_rect = goocanvas.Rect(x=400, y=300, width=400, height=300,
										 line_width=0, fill_color=color,
										 radius_x=30, radius_y=30)
		self._root.add_child(self._home_rect)

		for friend in data_model:
			self.add_friend(friend)

		data_model.connect('friend-added', self.__friend_added_cb)
		data_model.connect('friend-removed', self.__friend_removed_cb)

	def __theme_changed_cb(self, theme):
		color = self._theme.get_home_activities_color()
		self._home_rect.set_property("fill-color", color)
		color = self._theme.get_home_friends_color()
		self._friends_rect.set_property("fill-color", color)
		color = self._theme.get_home_mesh_color()
		self._mesh_rect.set_property("fill-color", color)

	def add_friend(self, friend):
		icon = FriendIcon(friend)
		self._root.add_child(icon)
		self._friend_to_child[friend] = icon

	def remove_friend(self, friend):
		icon = self._friend_to_child[friend]
		self._root.remove_child(self._root.find_child(icon))
		del self._friend_to_child[friend]

	def __friend_added_cb(self, data_model, friend):
		self.add_friend(friend)

	def __friend_removed_cb(self, data_model, friend):
		self.remove_friend(friend)

class FriendsView(goocanvas.CanvasView):
	def __init__(self, shell, data_model):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(data_model)
		self.set_model(canvas_model)

	def __item_view_created_cb(self, view, item_view, item):
		pass
