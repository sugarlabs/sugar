import logging

from sugar.chat.GroupChat import GroupChat

class ActivityChat(GroupChat):
	SERVICE_TYPE = "_olpc_activity_chat._udp"

	def __init__(self, activity):
		GroupChat.__init__(self)
		self._chat_service = None

		self._activity = activity
		self._pservice.connect('ServiceAppeared', self._service_appeared_cb)

		# Find an existing activity chat to latch onto
		#activity_ps = self._pservice.getActivity(activity.get_id())
		#service = activity.getServiceOfType(ActivityChat.SERVICE_TYPE)
		#if service is not None:
		#	self._service_appeared_cb(self._pservice, None, service)

	def _service_appeared_cb(self, pservice, buddy, service):
		if service.get_activity_id() != self._activity.get_id():
			return
		if service.get_type() != ActivityChat.SERVICE_TYPE:
			return
		if self._chat_service:
			return

		logging.debug('Activity chat service appeared, setup the stream.')
		# Ok, there's an existing chat service that we copy
		# parameters and such from
		addr = service.get_address()
		port = service.get_port()
		self._chat_service = self._pservice.share_activity(self._activity,
				stype=ActivityChat.SERVICE_TYPE, properties=None,
				address=addr, port=port)
		self._setup_stream(self._chat_service)

	def publish(self):
		"""Only called when we publish the activity this chat is tied to."""
		self._chat_service = self._pservice.share_activity(self._activity,
				stype=ActivityChat.SERVICE_TYPE)
		self._setup_stream(self._chat_service)
