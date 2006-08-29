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

		IconItem.__init__(self, icon_name=icon_name,
						  color=activity.get_color(), size=144)

		self._activity = activity

	def get_service(self):
		return self._activity.get_service()

class MeshGroup(goocanvas.Group):
	WIDTH = 1200.0 * 3.5
	HEIGHT = 900.0 * 3.5

	def __init__(self, shell, icon_layout, data_model):
		goocanvas.Group.__init__(self)
		self._shell = shell
		self._icon_layout = icon_layout

		self._theme = Theme.get_instance()
		self._theme.connect("theme-changed", self.__theme_changed_cb)

		color = self._theme.get_home_mesh_color()
		self._mesh_rect = goocanvas.Rect(width=MeshGroup.WIDTH,
										 height=MeshGroup.HEIGHT,
										 fill_color=color)
		self.add_child(self._mesh_rect)

		for activity in data_model:
			self.add_activity(activity)

		data_model.connect('activity-added', self.__activity_added_cb)

	def __theme_changed_cb(self, theme):
		pass

	def add_activity(self, activity):
		item = ActivityItem(activity)
		item.connect('clicked', self.__activity_clicked_cb)
		self._icon_layout.add_icon(item)
		self.add_child(item)

	def __activity_added_cb(self, data_model, activity):
		self.add_activity(activity)	

	def __activity_clicked_cb(self, item):
		self._shell.join_activity(item.get_service())
