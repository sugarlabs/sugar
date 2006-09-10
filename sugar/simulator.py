import os

import gtk
import gobject

from sugar.session.TestSession import TestSession
from sugar.presence import PresenceService
from sugar.p2p import Stream
from sugar import util

_PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class _SimulatedActivity:
	def __init__(self):
		self._id = util.unique_id()

	def get_id(self):
		return self._id

class _ShellOwner(object):
	def __init__(self, nick, color):
		self._pservice = PresenceService.get_instance()
		self._color = color
		self._nick = nick

	def announce(self):
		props = { 'color':  self._color.to_string() }
		self._service = self._pservice.register_service(self._nick,
				_PRESENCE_SERVICE_TYPE, properties=props)
		self._stream = Stream.Stream.new_from_service(self._service)
		self._stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")
		self._stream.register_reader_handler(self._handle_invite, "invite")

	def _handle_buddy_icon_request(self):
		return ''

	def _handle_invite(self, issuer, bundle_id, activity_id):
		return ''

class Bot:
	def __init__(self, nick, color):
		self._nick = nick
		self._color = color

		os.environ['SUGAR_NICK_NAME'] = self._nick

	def start(self):
		session = TestSession()
		session.start()

		PresenceService.start()

		owner = _ShellOwner(self._nick, self._color)
		owner.announce()

		gobject.timeout_add(1000, self._real_start)

		gtk.main()

	def _real_start(self):
		pservice = PresenceService.get_instance()

		if not pservice.get_owner().get_color():
			return True

		activity = _SimulatedActivity()
		properties = { 'title' : 'OLPC' }
		activity_type = '_GroupChatActivity_Sugar_redhat_com._udp'
		service = pservice.share_activity(activity, activity_type, properties)

		return False
