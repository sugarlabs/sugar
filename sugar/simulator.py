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

class _Timeline:
	def __init__(self, time_factor):
		self._time_factor = time_factor

	def add(self, action, minutes):
		gobject.timeout_add(int(1000 * 60 * minutes * self._time_factor),
							self._execute_action_cb, action)

	def _execute_action_cb(self, action):
		action.execute()
		return False

class ShareActivityAction:
	def __init__(self, title, activity_type):
		self._title = title
		self._type = activity_type

	def execute(self):
		activity = _SimulatedActivity()
		properties = { 'title' : self._title }
		
		pservice = PresenceService.get_instance()
		pservice.share_activity(activity, self._type, properties)		

class Bot:
	def __init__(self, nick, color):
		self._nick = nick
		self._color = color
		self._timeline = _Timeline(0.01)

		os.environ['SUGAR_NICK_NAME'] = self._nick

	def start(self):
		session = TestSession()
		session.start()

		PresenceService.start()

		owner = _ShellOwner(self._nick, self._color)
		owner.announce()

		gobject.timeout_add(1000, self._real_start)

		gtk.main()

	def add_action(self, action, minutes):
		self._timeline.add(action, minutes)

	def _real_start(self):
		pservice = PresenceService.get_instance()

		if not pservice.get_owner().get_color():
			return True

		return False
