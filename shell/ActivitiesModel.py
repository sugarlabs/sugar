import xml.sax.saxutils

import gobject

from sugar.presence.PresenceService import PresenceService

class ActivityInfo:
	def __init__(self, service):
		self._service = service
	
	def get_id(self):
		activity_id = self._service.get_one_property('activity_id')
		
	def get_type(self):
		return self._service.get_type()
	
	def get_title(self):
		escaped_title = self._service.get_one_property('Title')
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
		
		self._pservice = PresenceService.get_instance()
		self._pservice.connect("activity-announced", self._on_activity_announced_cb)
		self._pservice.connect("new-service-adv", self._on_new_service_adv_cb)
		self._pservice.start()

	def add_activity(self, service):
		activity_info = ActivityInfo(service)
		self._activities.append(activity_info)
		self.emit('activity-added', activity_info)

	def __iter__(self):
		return self._activities.__iter__()

	def _on_new_service_adv_cb(self, pservice, activity_id, short_stype):
		if activity_id:
			self._pservice.track_service_type(short_stype)

	def _on_activity_announced_cb(self, pservice, service, buddy):
		# FIXME We should not hard code activity types here
		if service.get_type() == "_web_olpc._udp":
			self.add_activity(service)
