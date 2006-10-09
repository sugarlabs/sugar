import random

import gobject

from sugar.presence import PresenceService
from sugar.graphics.iconcolor import IconColor
from sugar.p2p import Stream
from sugar import util

_PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class _BotService(object):
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

class _ShareChatAction(object):
	def __init__(self, bot, title):
		self._bot = bot
		self._title = title
		self._id = util.unique_id() 

	def execute(self):
		name = "%s [%s]" % (self._bot.name, self._id)
		stype = '_GroupChatActivity_Sugar_redhat_com._udp'
		properties = { 'title' : self._title,
					   'color' : self._bot.color.to_string() }
		address = u"232.%d.%d.%d" % (random.randint(0, 254),
									 random.randint(1, 254),
									 random.randint(1, 254))

		pservice = PresenceService.get_instance()
		pservice.register_service(name, stype, properties, address)

class _WaitAction(object):
	def __init__(self, bot, seconds):
		self._bot = bot
		self._seconds = seconds
	
	def execute(self):
		self._bot._pause_queue(self._seconds)

class Bot(object):
	def __init__(self):
		self.name = util.unique_id()
		self.color = IconColor()
		self.icon = None

		self._queue = []

	def wait(self, seconds):
		action = _WaitAction(self, seconds)
		self._queue.append(action)

	def share_chat(self, title):
		action = _ShareChatAction(self, title)
		self._queue.append(action)

	def start(self):
		self._service = _BotService(self)
		self._service.announce()

		self._start_queue()

	def _idle_cb(self):
		self._next_action()
		return True

	def _pause_done_cb(self):
		self._start_queue()
		return False

	def _start_queue(self):
		self._queue_sid = gobject.idle_add(self._idle_cb)

	def _pause_queue(self, seconds):
		gobject.source_remove(self._queue_sid)
		gobject.timeout_add(int(seconds * 1000), self._pause_done_cb)

	def _next_action(self):
		if len(self._queue) > 0:
			action = self._queue.pop(0)
			action.execute()
