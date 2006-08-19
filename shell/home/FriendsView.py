import random

import goocanvas

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, data_model):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		item = goocanvas.Rect(width=1200, height=900,
							  fill_color="#d8d8d8")
		root.add_child(item)

		for friend in data_model:
			self.add_friend(friend)

		data_model.connect('friend-added', self.__friend_added_cb)

	def add_friend(self, friend):
		root = self.get_root_item()

		icon = IconItem('stock-buddy', IconColor(), 48)
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
