import random
import base64

from sugar.presence import Service
from sugar.presence import Buddy
from sugar.presence import PresenceService
from sugar.p2p import Stream

class Bot:
	def __init__(self, nick, icon_path):
		self._nick = nick
		self._icon_path = icon_path
	
	def start(self):
		fd = open(self._icon_path, "r")
		self._icon = fd.read()
		fd.close()

		# Our presence service
		port = random.randint(40000, 65000)
		properties = {}
		self._service = Service.Service(self._nick, Buddy.PRESENCE_SERVICE_TYPE,
			domain="", address=None, port=port, properties=properties)

		self._icon_stream = Stream.Stream.new_from_service(self._service)
		self._icon_stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")

		# Announce ourselves to the world
		self._pservice = PresenceService.PresenceService.get_instance()
		self._pservice.start()
		self._pservice.register_service(self._service)

	def _handle_buddy_icon_request(self):
		"""XMLRPC method, return the owner's icon encoded with base64."""
		if self._icon:
			return base64.b64encode(self._icon)
		return ""
