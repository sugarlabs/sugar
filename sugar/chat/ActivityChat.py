import logging

from sugar.chat.GroupChat import GroupChat

class ActivityChat(GroupChat):
	SERVICE_TYPE = "_olpc_activity_chat._udp"
	SERVICE_PORT = 6200

	def __init__(self, activity):
		GroupChat.__init__(self)
		self._activity = activity
		self._pservice.connect('service-appeared', self._service_appeared_cb)
		self._pservice.track_service_type(ActivityChat.SERVICE_TYPE)
		service = self._pservice.get_activity_service(activity, ActivityChat.SERVICE_TYPE)
		if service is not None:
			self._service_appeared_cb(self._pservice, None, service)

	def _service_appeared_cb(self, pservice, buddy, service):
		if service.get_activity_id() == self._activity.get_id():
			if service.get_type() == ActivityChat.SERVICE_TYPE:
				logging.debug('Group chat service appeared, setup the stream.')
				self._setup_stream(service)

	def publish(self):
		service = self._pservice.share_activity(self._activity,
				stype = ActivityChat.SERVICE_TYPE, port = ActivityChat.SERVICE_PORT)
