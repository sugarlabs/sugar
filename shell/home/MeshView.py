import random

import goocanvas

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor
from sugar import conf

import Theme

class ActivityItem(IconItem):
	def __init__(self, activity):
		registry = conf.get_activity_registry()
		info = registry.get_activity(activity.get_type())
		icon_name = info.get_icon()

		IconItem.__init__(self, icon_name, IconColor(), 48)

		self._activity = activity

	def get_service(self):
		return self._activity.get_service()

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
		self._friends_rect = goocanvas.Rect(x=350, y=280, width=500, height=340,
										 line_width=0, fill_color=color,
										 radius_x=30, radius_y=30)
		root.add_child(self._friends_rect)

		color = self._theme.get_home_activities_color()
		self._home_rect = goocanvas.Rect(x=480, y=360, width=240, height=180,
										 line_width=0, fill_color=color,
										 radius_x=30, radius_y=30)
		root.add_child(self._home_rect)

		for activity in data_model:
			self.add_activity(activity)

		data_model.connect('activity-added', self.__activity_added_cb)

	def __theme_changed_cb(self, theme):
		pass

	def add_activity(self, activity):
		root = self.get_root_item()

		item = ActivityItem(activity, self._registry)
		item.set_property('x', random.random() * 1100)
		item.set_property('y', random.random() * 800)
		root.add_child(item)

	def __activity_added_cb(self, data_model, activity):
		self.add_activity(activity)	

class MeshView(goocanvas.CanvasView):
	def __init__(self, shell, data_model):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(data_model)
		self.set_model(canvas_model)

	def __activity_button_press_cb(self, view, target, event, service):
		self._shell.join_activity(service)

	def __item_view_created_cb(self, view, item_view, item):
		if isinstance(item, ActivityItem):
			item_view.connect("button_press_event",
							  self.__activity_button_press_cb,
							  item.get_service())
