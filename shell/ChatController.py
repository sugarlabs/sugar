from sugar import env
from sugar.chat.BuddyChat import BuddyChat
from sugar.activity import ActivityFactory
from sugar.presence.PresenceService import PresenceService
from sugar.p2p.Stream import Stream

class ChatController:
	def __init__(self, shell):
		self._shell = shell

	def listen(self):
		self._pservice = PresenceService()

		self._pservice.register_service_type(BuddyChat.SERVICE_TYPE)
		self._service = self._pservice.register_service(env.get_nick_name(),
														BuddyChat.SERVICE_TYPE)

		self._buddy_stream = Stream.new_from_service(self._service)
		self._buddy_stream.set_data_listener(self._recv_message)

	def _recv_message(self, address, message):
		[nick, msg] = Chat.deserialize_message(message)
		buddy = self._pservice.get_buddy_by_name(nick)
		if buddy:
			activity = self._shell.start_activity('com.redhat.Sugar.ChatActivity')
			service = buddy.get_service_of_type(BuddyChat.SERVICE_TYPE)
			activity.execute('start', service.object_path())
			activity.execute('message', message)
