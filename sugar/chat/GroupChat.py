import logging

from sugar.chat.Chat import Chat
from sugar.presence.Service import Service
from sugar.p2p.Stream import Stream
from sugar.presence.PresenceService import PresenceService 

class GroupChat(Chat):
	SERVICE_TYPE = "_olpc_group_chat._udp"
	SERVICE_PORT = 6200

	def __init__(self, activity):
		Chat.__init__(self)
		self._chats = {}
		self._activity = activity

		self._pservice = PresenceService.get_instance()
		self._pservice.start()		
		self._pservice.connect('service-appeared', self._service_appeared_cb)
		self._pservice.track_service_type(GroupChat.SERVICE_TYPE)

		# FIXME remove, when we join the activity this will happen automatically
		# (Once we have a global presence service)
		self._pservice.track_activity(activity.get_id())

	def _service_appeared_cb(self, pservice, buddy, service):
		if service.get_type() == GroupChat.SERVICE_TYPE:
			logging.debug('Group chat service appeared, setup the stream.')
			self._setup_stream(service)

	def publish(self):
		service = self._pservice.share_activity(self._activity,
				stype = GroupChat.SERVICE_TYPE, port = GroupChat.SERVICE_PORT)

	def _setup_stream(self, service):
		self._group_stream = Stream.new_from_service(service)
		self._group_stream.set_data_listener(self._group_recv_message)
		self._stream_writer = self._group_stream.new_writer()

	def _group_recv_message(self, buddy, msg):
		self.recv_message(buddy, msg)
