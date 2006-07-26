import xml.sax.saxutils

import gobject

from sugar.presence.PresenceService import PresenceService

class ActivityInfo:
	def __init__(self, service):
		self._service = service
	
	def get_id(self):
		activity_id = self._service.get_activity_id()
		
	def get_type(self):
		return self._service.get_type()
	
	def get_title(self):
		escaped_title = self._service.get_published_value('Title')
		title = xml.sax.saxutils.unescape(escaped_title)
		return title
	
	def get_service(self):
		return self._service

class ActivitiesModel(gobject.GObject):
	__gsignals__ = {
		'activity-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						    ([gobject.TYPE_PYOBJECT])),
		'activity-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						    ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		
		self._activities = []
		
		self._pservice = PresenceService()
		self._pservice.connect("activity-appeared", self._on_activity_announced_cb)

	def add_activity(self, service):
		activity_info = ActivityInfo(service)
		self._activities.append(activity_info)
		self.emit('activity-added', activity_info)

	def __iter__(self):
		return self._activities.__iter__()

	def _on_activity_announced_cb(self, pservice, activity):
		# FIXME We should not hard code activity types here
		services = activity.get_services_of_type("_web_olpc._udp")
		if len(services) > 0:
			self.add_activity(services[0])
