#!/usr/bin/python
import os

import gtk

from sugar.session.TestSession import TestSession
from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor
from sugar.p2p import Stream
from sugar import util

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class SimulatedActivity:
	def __init__(self):
		self._id = util.unique_id()

	def get_id(self):
		return self._id

class ShellOwner(object):
	def __init__(self):
		self._pservice = PresenceService.get_instance()
		self._color = IconColor()
		self._nick = 'kiu'

	def announce(self):
		props = { 'color':  self._color.to_string() }
		self._service = self._pservice.register_service(self._nick,
				PRESENCE_SERVICE_TYPE, properties=props)
		self._stream = Stream.Stream.new_from_service(self._service)
		self._stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")
		self._stream.register_reader_handler(self._handle_invite, "invite")

	def _handle_buddy_icon_request(self):
		return ''

	def _handle_invite(self, issuer, bundle_id, activity_id):
		return ''

os.environ['SUGAR_NICK_NAME'] = 'kiu'

session = TestSession()
session.start()

PresenceService.start()

owner = ShellOwner()
owner.announce()

pservice = PresenceService.get_instance()

activity = SimulatedActivity()
properties = { 'title' : 'OLPC' }
activity_type = '_GroupChatActivity_Sugar_redhat_com._udp'
service = pservice.share_activity(activity, activity_type, properties)

gtk.main()
