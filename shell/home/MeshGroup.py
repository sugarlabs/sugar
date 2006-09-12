import random

import goocanvas

import conf
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor
from sugar.presence import PresenceService
from home.IconLayout import IconLayout

class ActivityItem(IconItem):
	def __init__(self, activity, service):
		self._service = service
		self._activity = activity

		IconItem.__init__(self, icon_name=self.get_icon_name(),
						  color=self.get_color(), size=96)

	def get_id(self):
		return self._activity.get_id()
		
	def get_icon_name(self):
		registry = conf.get_activity_registry()
		info = registry.get_activity_from_type(self._service.get_type())

		return info.get_icon()
	
	def get_color(self):
		return IconColor(self._activity.get_color())

	def get_service(self):
		return self._service

class MeshGroup(goocanvas.Group):
	def __init__(self, shell):
		goocanvas.Group.__init__(self)
		self._shell = shell
		self._icon_layout = IconLayout(1200, 900)
		self._activities = {}

		self._pservice = PresenceService.get_instance()
		self._pservice.connect("service-appeared", self._service_appeared_cb)
		self._pservice.connect('activity-disappeared', self._activity_disappeared_cb)

		for service in self._pservice.get_services():
			self._check_service(service)

	def _service_appeared_cb(self, pservice, service):
		self._check_service(service)

	def _check_service(self, service):
		registry = conf.get_activity_registry()
		if registry.get_activity_from_type(service.get_type()) != None:
			activity_id = service.get_activity_id()
			if not self.has_activity(activity_id):
				activity = self._pservice.get_activity(activity_id)
				if activity != None:
					self.add_activity(activity, service)

	def has_activity(self, activity_id):
		return self._activities.has_key(activity_id)

	def add_activity(self, activity, service):
		item = ActivityItem(activity, service)
		item.connect('clicked', self._activity_clicked_cb)
		self._icon_layout.add_icon(item)
		self.add_child(item)

		self._activities[item.get_id()] = item

	def _activity_disappeared_cb(self, activity):
		print 'remove'
		if self._activities.has_key(activity.get_id()):
			self.remove_child(self._activities[activity.get_id()])
			del self._activities[activity.get_id()]

	def _activity_clicked_cb(self, item):
		default_type = item.get_service().get_type()
		registry = conf.get_activity_registry()

		bundle_id = registry.get_activity_from_type(default_type).get_id()
		activity_id = item.get_id()

		self._shell.join_activity(bundle_id, activity_id)
