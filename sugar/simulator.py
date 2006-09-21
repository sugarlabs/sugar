import os

import gtk
import gobject
import base64
import dbus

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

class _SimulatedShellOwner(object):
	def __init__(self, nick, color, icon_file=None):
		self._pservice = PresenceService.get_instance()
		self._color = color
		self._nick = nick

		self._icon = None
		if icon_file:
			fd = open(icon_file, "r")
			self._icon = fd.read()
			fd.close()

	def announce(self):
		props = { 'color':  self._color.to_string() }
		self._service = self._pservice.register_service(self._nick,
				_PRESENCE_SERVICE_TYPE, properties=props)
		self._stream = Stream.Stream.new_from_service(self._service)
		self._stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")
		self._stream.register_reader_handler(self._handle_invite, "invite")

	def _handle_buddy_icon_request(self):
		if self._icon:
			return base64.b64encode(self._icon)
		return ''

	def _handle_invite(self, issuer, bundle_id, activity_id):
		return ''

	def set_current_activity(self, activity_id):
		self._service.set_published_value('curact', dbus.String(activity_id))

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
	def __init__(self, title, activity_type, callback=None):
		self._title = title
		self._type = activity_type
		self._callback = callback

	def execute(self):
		activity = _SimulatedActivity()
		properties = { 'title' : self._title }
		
		pservice = PresenceService.get_instance()
		act_service = pservice.share_activity(activity, self._type, properties)		
		if self._callback is not None:
			self._callback(activity, act_service)

class Bot:
	def __init__(self, nick, color):
		self._nick = nick
		self._color = color
		self._timeline = _Timeline(0.01)
		self._owner = None
		self._icon_file = None

		os.environ['SUGAR_NICK_NAME'] = nick
		os.environ['SUGAR_COLOR'] = color.to_string()

	def start(self):
		session = TestSession()
		session.start()

		PresenceService.start()

		self._owner = _SimulatedShellOwner(self._nick, self._color, self._icon_file)
		self._owner.announce()

		self._pservice = PresenceService.get_instance()

		gtk.main()

	def add_action(self, action, minutes):
		self._timeline.add(action, minutes)
