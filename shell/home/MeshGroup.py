import random

import goocanvas

import conf
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor
from sugar.presence import PresenceService

class ActivityItem(IconItem):
	def __init__(self, service):
		self._service = service

		IconItem.__init__(self, icon_name=self.get_icon_name(),
						  color=self.get_color(), size=144)

	def get_id(self):
		return self._service.get_activity_id()
		
	def get_icon_name(self):
		registry = conf.get_activity_registry()
		info = registry.get_activity_from_type(self._service.get_type())

		return info.get_icon()
	
	def get_color(self):
		pservice = PresenceService.get_instance()
		activity = pservice.get_activity(self.get_id())
		return IconColor(activity.get_color())

	def get_service(self):
		return self._service

class MeshGroup(goocanvas.Group):
	def __init__(self, shell, icon_layout):
		goocanvas.Group.__init__(self)
		self._shell = shell
		self._icon_layout = icon_layout
		self._activities = {}

		pservice = PresenceService.get_instance()
		pservice.connect("service-appeared", self.__service_appeared_cb)

		for service in pservice.get_services():
			self.__check_service(service)

	def __service_appeared_cb(self, pservice, service):
		self.__check_service(service)

	def __check_service(self, service):
		registry = conf.get_activity_registry()
		if registry.get_activity_from_type(service.get_type()) != None:
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
		default_type = item.get_service().get_type()
		registry = conf.get_activity_registry()

		bundle_id = registry.get_activity_from_type(default_type).get_id()
		activity_id = item.get_service().get_activity_id()

		self._shell.join_activity(bundle_id, activity_id)
