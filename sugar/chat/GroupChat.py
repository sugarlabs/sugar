import logging

from sugar.chat.Chat import Chat
from sugar.p2p.Stream import Stream
from sugar.presence.PresenceService import PresenceService
import sugar.env

class GroupChat(Chat):
	def __init__(self):
		Chat.__init__(self)
		self._pservice = PresenceService.get_instance()
		self._pservice.start()
		self._group_stream = None

	def _setup_stream(self, service):
		self._group_stream = Stream.new_from_service(service)
		self._group_stream.set_data_listener(self._group_recv_message)
		self._stream_writer = self._group_stream.new_writer()

	def _group_recv_message(self, address, msg):
		pservice = PresenceService.get_instance()
		[nick, msg] = self.deserialize_message(msg)
		buddy = pservice.get_buddy_by_nick_name(nick)
		if buddy:
			self.recv_message(buddy, msg)
		else:
			logging.error('The buddy %s is not present.' % (nick))
