from sugar import env
from sugar.chat.BuddyChat import BuddyChat
from sugar.activity import ActivityFactory
from sugar.presence.PresenceService import PresenceService
from sugar.p2p.Stream import Stream
from sugar.chat.Chat import Chat

class ChatController:
	def __init__(self, shell):
		self._shell = shell
		self._id_to_name = {}
		self._name_to_chat = {}

		self._shell.connect('activity-closed', self.__activity_closed_cb)

	def __activity_closed_cb(self, shell, activity):
		activity_id = activity.get_id()
		if self._id_to_name.has_key(activity_id):
			name = self._id_to_name[activity_id]
			del self._name_to_chat[name]
			del self._id_to_name[activity_id]

	def listen(self):
		self._pservice = PresenceService()

		self._pservice.register_service_type(BuddyChat.SERVICE_TYPE)
		self._service = self._pservice.register_service(env.get_nick_name(),
														BuddyChat.SERVICE_TYPE)

		self._buddy_stream = Stream.new_from_service(self._service)
		self._buddy_stream.set_data_listener(self._recv_message)

	def open_chat_activity(self, buddy):
		service = buddy.get_service_of_type(BuddyChat.SERVICE_TYPE)
		if service:
			activity = self._shell.start_activity('com.redhat.Sugar.ChatActivity')
			activity.execute('connect', [service.object_path()])
			self._name_to_chat[buddy.get_name()] = activity
			self._id_to_name[activity.get_id()] = buddy.get_name()

	def _get_chat_activity(self, buddy):
		nick = buddy.get_name()
		if not self._name_to_chat.has_key(nick):
			self.open_chat_activity(buddy)
		return self._name_to_chat[nick]

	def _recv_message(self, address, message):
		[nick, msg] = Chat.deserialize_message(message)
		buddy = self._pservice.get_buddy_by_name(nick)
		if buddy:
			activity = self._get_chat_activity(buddy)
			if activity:
				activity.execute('message', [message])
