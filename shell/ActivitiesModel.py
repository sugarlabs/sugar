import xml.sax.saxutils

import gobject

from sugar.presence.PresenceService import PresenceService

class ActivityInfo:
	def __init__(self, service):
		self._service = service
	
	def get_id(self):
		activity_id = self._service.get_id()
		
	def get_type(self):
		# FIXME
		return "_web_olpc._udp"
	
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
		self.add_activity(activity)
