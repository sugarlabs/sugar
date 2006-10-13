from sugar.p2p.Stream import Stream
from sugar.presence import PresenceService

class _Marshaller(object):
	def marshal(self, title, address):
		return title + '\n' + address

	def demarshal(self, message):
		return message.split('\n')

class LinksController(object):
	def __init__(self, service, model):
		self._model = model

		self._pservice = PresenceService.get_instance()
		self._marshaller = _Marshaller()

		self._stream = Stream.new_from_service(service)
		self._stream.set_data_listener(self._recv_message)
		self._stream_writer = self._stream.new_writer()

	def post_link(self, title, address):
		message = self._marshaller.marshal(title, address)
		self._stream_writer.write(message)

	def _recv_message(self, address, msg):
		buddy = self._pservice.get_buddy_by_address(address)
		if buddy:
			link = self._marshaller.demarshal(msg)
			self._model.add_link(buddy, *link)
