from sugar.presence import PresenceService
from sugar.graphics.iconcolor import IconColor
from sugar.p2p import Stream
from sugar import util

_PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class BotService(object):
	def __init__(self, bot):
		self._bot = bot

	def announce(self):
		props = { 'color':  self._bot.color.to_string() }
		pservice = PresenceService.get_instance()
		self._service = pservice.register_service(self._bot.name,
							_PRESENCE_SERVICE_TYPE, properties=props)

		self._stream = Stream.Stream.new_from_service(self._service)
		self._stream.register_reader_handler(
						self._handle_buddy_icon_request, "get_buddy_icon")
		self._stream.register_reader_handler(
						self._handle_invite, "invite")

	def _handle_buddy_icon_request(self):
		if self._bot.icon:
			fd = open(self._bot.icon, "r")
			icon_data = fd.read()
			fd.close()
			if icon_data:
				return base64.b64encode(self._icon)
		return ''

	def _handle_invite(self, issuer, bundle_id, activity_id):
		return ''

	def set_current_activity(self, activity_id):
		self._service.set_published_value('curact', dbus.String(activity_id))

class Bot(object):
	def __init__(self):
		self.name = util.unique_id()
		self.color = IconColor()
		self.icon = None

	def start(self):
		self._service = BotService(self)
		self._service.announce()
