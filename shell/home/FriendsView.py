import random

import goocanvas

from sugar.canvas.IconItem import IconItem

import Theme

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, data_model):
		goocanvas.CanvasModelSimple.__init__(self)
		self._theme = Theme.get_instance()
		self._theme.connect("theme-changed", self.__theme_changed_cb)

		root = self.get_root_item()

		color = self._theme.get_home_mesh_color()
		self._mesh_rect = goocanvas.Rect(width=1200, height=900,
										 fill_color=color)
		root.add_child(self._mesh_rect)

		color = self._theme.get_home_friends_color()
		self._friends_rect = goocanvas.Rect(x=100, y=100, width=1000, height=700,
											line_width=0, fill_color=color,
											radius_x=30, radius_y=30)
		root.add_child(self._friends_rect)

		color = self._theme.get_home_activities_color()
		self._home_rect = goocanvas.Rect(x=400, y=300, width=400, height=300,
										 line_width=0, fill_color=color,
										 radius_x=30, radius_y=30)
		root.add_child(self._home_rect)

		for friend in data_model:
			self.add_friend(friend)

		data_model.connect('friend-added', self.__friend_added_cb)

	def __theme_changed_cb(self, theme):
		color = self._theme.get_home_activities_color()
		self._home_rect.set_property("fill-color", color)
		color = self._theme.get_home_friends_color()
		self._friends_rect.set_property("fill-color", color)
		color = self._theme.get_home_mesh_color()
		self._mesh_rect.set_property("fill-color", color)

	def add_friend(self, friend):
		root = self.get_root_item()

		icon = IconItem('stock-buddy', friend.get_color(), 48)
		icon.set_property('x', random.random() * 1100)
		icon.set_property('y', random.random() * 800)

		root.add_child(icon)

	def __friend_added_cb(self, data_model, friend):
		self.add_friend(friend)	

class FriendsView(goocanvas.CanvasView):
	def __init__(self, shell, data_model):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(data_model)
		self.set_model(canvas_model)

	def __item_view_created_cb(self, view, item_view, item):
		pass
