import xml.sax.saxutils

import gobject

from sugar.presence.PresenceService import PresenceService
from ActivityRegistry import ActivityRegistry

class ActivityInfo:
	def __init__(self, service):
		self._service = service
	
	def get_id(self):
		return self._service.get_activity_id()
		
	def get_type(self):
		return self._service.get_type()
	
	def get_title(self):
		return "FIXME Title"
	
	def get_service(self):
		return self._service

class ActivitiesModel(gobject.GObject):
	__gsignals__ = {
		'activity-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						    ([gobject.TYPE_PYOBJECT])),
		'activity-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						    ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self, registry):
		gobject.GObject.__init__(self)
		
		self._activities = []
		self._registry = registry
		
		self._pservice = PresenceService()
		self._pservice.connect("service-appeared", self.__service_appeared_cb)

	def add_activity(self, service):
		activity_info = ActivityInfo(service)
		self._activities.append(activity_info)
		self.emit('activity-added', activity_info)

	def __iter__(self):
		return self._activities.__iter__()

	def __service_appeared_cb(self, pservice, service):
		if self._registry.get_activity(service.get_type()) != None:
			self.add_activity(service)
