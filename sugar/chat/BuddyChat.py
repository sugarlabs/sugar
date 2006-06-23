from sugar.chat.Chat import Chat
from sugar.p2p.Stream import Stream

class BuddyChat(Chat):
	SERVICE_TYPE = "_olpc_buddy_chat._tcp"

	def __init__(self, service):
		Chat.__init__(self)

		self._stream = Stream.new_from_service(service, False)
		self._stream_writer = self._stream.new_writer(service)

	def _recv_message_cb(self, address, msg):
		self.recv_message(msg)
