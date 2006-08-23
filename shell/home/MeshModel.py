import gobject

from sugar.presence import PresenceService
from sugar import conf

class ActivityInfo:
	def __init__(self, service):
		self._service = service
	
	def get_id(self):
		return self._service.get_activity_id()
		
	def get_type(self):
		return self._service.get_type()
	
	def get_title(self):
		return self._service.get_published_value('title')
	
	def get_service(self):
		return self._service

class MeshModel(gobject.GObject):
	__gsignals__ = {
		'activity-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						    ([gobject.TYPE_PYOBJECT])),
		'activity-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						    ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		
		self._activities = {}
		
		self._pservice = PresenceService.get_instance()
		self._pservice.connect("service-appeared", self.__service_appeared_cb)

		for service in self._pservice.get_services():
			self.__check_service(service)

	def has_activity(self, activity_id):
		return self._activities.has_key(activity_id)

	def add_activity(self, service):
		activity_info = ActivityInfo(service)
		self._activities[activity_info.get_id()] = (activity_info)
		self.emit('activity-added', activity_info)

	def __iter__(self):
		activities = self._activities.values()
		return activities.__iter__()

	def __service_appeared_cb(self, pservice, service):
		self.__check_service(service)

	def __check_service(self, service):
		registry = conf.get_activity_registry()
		if registry.get_activity(service.get_type()) != None:
			if not self.has_activity(service.get_activity_id()):
				self.add_activity(service)
