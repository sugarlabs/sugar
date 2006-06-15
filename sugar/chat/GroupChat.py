from sugar.chat.Chat import Chat

class GroupChat(Chat):
	def __init__(self):
		Chat.__init__(self, self)
		self._chats = {}

	def get_group(self):
		return self._group

	def new_buddy_writer(self, buddy):
		service = buddy.get_service(CHAT_SERVICE_TYPE)
		return self._buddy_stream.new_writer(service)

	def _start(self):
		name = self._group.get_owner().get_nick_name()

		# Group controls the Stream for incoming messages for
		# specific buddy chats
		buddy_service = Service(name, CHAT_SERVICE_TYPE, CHAT_SERVICE_PORT)
		self._buddy_stream = Stream.new_from_service(buddy_service, self._group)
		self._buddy_stream.set_data_listener(getattr(self, "_buddy_recv_message"))
		buddy_service.register(self._group)

		# Group chat Stream
		group_service = Service(name, GROUP_CHAT_SERVICE_TYPE,
						  GROUP_CHAT_SERVICE_PORT,
						  GROUP_CHAT_SERVICE_ADDRESS)
		self._group.add_service(group_service)

		self._group_stream = Stream.new_from_service(group_service, self._group)
		self._group_stream.set_data_listener(self._group_recv_message)
		self._stream_writer = self._group_stream.new_writer()

	def _group_recv_message(self, buddy, msg):
		self.recv_message(buddy, msg)

	def _buddy_recv_message(self, buddy, msg):
		if not self._chats.has_key(buddy):
			chat = BuddyChat(self, buddy)
			self._chats[buddy] = chat
			chat.connect_to_shell()
		else:
			chat = self._chats[buddy]
		chat.recv_message(buddy, msg)
