import random

import goocanvas

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor
from sugar.presence import PresenceService
from sugar import conf

import Theme

class ActivityItem(IconItem):
	def __init__(self, service):
		self._service = service

		IconItem.__init__(self, icon_name=self.get_icon_name(),
						  color=self.get_color(), size=144)

	def get_id(self):
		return self._service.get_activity_id()
		
	def get_icon_name(self):
		registry = conf.get_activity_registry()
		info = registry.get_activity(self._service.get_type())

		return info.get_icon()
	
	def get_color(self):
		pservice = PresenceService.get_instance()
		activity = pservice.get_activity(self.get_id())
		return IconColor(activity.get_color())

	def get_service(self):
		return self._service

class MeshGroup(goocanvas.Group):
	WIDTH = 1200.0 * 3.5
	HEIGHT = 900.0 * 3.5

	def __init__(self, shell, icon_layout):
		goocanvas.Group.__init__(self)
		self._shell = shell
		self._icon_layout = icon_layout
		self._activities = {}

		self._theme = Theme.get_instance()

		color = self._theme.get_home_mesh_color()
		self._mesh_rect = goocanvas.Rect(width=MeshGroup.WIDTH,
										 height=MeshGroup.HEIGHT,
										 fill_color=color)
		self.add_child(self._mesh_rect)

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("service-appeared", self.__service_appeared_cb)

		for service in self._pservice.get_services():
			self.__check_service(service)

	def __service_appeared_cb(self, pservice, service):
		self.__check_service(service)

	def __check_service(self, service):
		registry = conf.get_activity_registry()
		if registry.get_activity(service.get_type()) != None:
			if not self.has_activity(service.get_activity_id()):
				self.add_activity(service)

	def has_activity(self, activity_id):
		return self._activities.has_key(activity_id)

	def add_activity(self, service):
		item = ActivityItem(service)
		item.connect('clicked', self.__activity_clicked_cb)

		self._icon_layout.add_icon(item)
		self.add_child(item)

		self._activities[item.get_id()] = item

	def __activity_clicked_cb(self, item):
		self._shell.join_activity(item.get_service())
