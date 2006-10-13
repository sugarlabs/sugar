from sugar.p2p.Stream import Stream
from sugar.presence import PresenceService

class _Marshaller(object):
	def __init__(self, title, address):
		pservice = PresenceService.get_instance()
		name = pservice.get_owner().get_name()
		self._message = name + '\n' + title + '\n' + address

	def get_message(self):
		return self._message

class _Demarshaller(object):
	def __init__(self, message):
		self._pservice = PresenceService.get_instance()
		self._split_msg = message.split('\n')

	def get_buddy(self):
		return self._pservice.get_buddy_by_name(self._split_msg[0])

	def get_title(self):
		return self._split_msg[1]

	def get_address(self):
		return self._split_msg[2]

class LinksController(object):
	def __init__(self, service, model):
		self._model = model

		self._stream = Stream.new_from_service(service)
		self._stream.set_data_listener(self._recv_message)
		self._stream_writer = self._stream.new_writer()

	def post_link(self, title, address):
		marshaller = _Marshaller(title, address)
		self._stream_writer.write(marshaller.get_message())

	def _recv_message(self, address, msg):
		demarshaller = _Demarshaller(msg)
		buddy = demarshaller.get_buddy()
		if buddy:
			self._model.add_link(buddy, demarshaller.get_title(),
								 demarshaller.get_address())
