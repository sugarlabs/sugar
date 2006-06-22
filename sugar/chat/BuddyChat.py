from sugar.activity.Activity import Activity

class BuddyChat(Activity):
	SERVICE_TYPE = "_olpc_buddy_chat._tcp"

	def __init__(self, service):
		Chat.__init__(self)

		self._stream = Stream.new_from_service(service)
		self._stream.set_data_listener(self._recv_message)
		self._stream_writer = self._group_stream.new_writer()

	def recv_message(self, address, msg):
		print msg
#		Chat.recv_message(self, self._buddy, msg)
