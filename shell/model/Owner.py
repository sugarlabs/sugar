import os
import random
import base64
import time
import gobject

import conf
from sugar import env
import logging
from sugar.p2p import Stream
from sugar.presence import PresenceService
from sugar import util
from model.Invites import Invites
import dbus

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class ShellOwner(object):
	"""Class representing the owner of this machine/instance.  This class
	runs in the shell and serves up the buddy icon and other stuff.  It's the
	server portion of the Owner, paired with the client portion in Buddy.py."""
	def __init__(self, shell_model):
		profile = conf.get_profile()

		self._shell_model = shell_model
		self._shell_model.connect('activity-changed', self.__activity_changed_cb)

		self._nick = profile.get_nick_name()
		user_dir = profile.get_path()

		self._icon = None
		self._icon_hash = ""
		for fname in os.listdir(user_dir):
			if not fname.startswith("buddy-icon."):
				continue
			fd = open(os.path.join(user_dir, fname), "r")
			self._icon = fd.read()
			if self._icon:
				# Get the icon's hash
				import md5, binascii
				digest = md5.new(self._icon).digest()
				self._icon_hash = util.printable_hash(digest)
			fd.close()
			break

		self._pservice = PresenceService.get_instance()

		self._invites = Invites()

		self._last_activity_update = time.time()
		self._pending_activity_update_timer = None
		self._pending_activity_update = None

	def get_invites(self):
		return self._invites

	def get_name(self):
		return self._nick

	def announce(self):
		# Create and announce our presence
		color = conf.get_profile().get_color()
		props = {'color': color.to_string(), 'icon-hash': self._icon_hash}
		self._service = self._pservice.register_service(self._nick,
				PRESENCE_SERVICE_TYPE, properties=props)
		logging.debug("Owner '%s' using port %d" % (self._nick, self._service.get_port()))
		self._icon_stream = Stream.Stream.new_from_service(self._service)
		self._icon_stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")
		self._icon_stream.register_reader_handler(self._handle_invite, "invite")

	def _handle_buddy_icon_request(self):
		"""XMLRPC method, return the owner's icon encoded with base64."""
		if self._icon:
			return base64.b64encode(self._icon)
		return ""

	def _handle_invite(self, issuer, bundle_id, activity_id):
		"""XMLRPC method, called when the owner is invited to an activity."""
		self._invites.add_invite(issuer, bundle_id, activity_id)
		return ''

	def __update_advertised_current_activity_cb(self):
		self._last_activity_update = time.time()
		self._pending_activity_update_timer = None
		actid = self._pending_activity_update
		if not actid:
			actid = ""
		self._service.set_published_value('curact', dbus.String(actid))
		return False

	def __activity_changed_cb(self, shell_model, activity_id):
		"""Update our presence service with the latest activity, but no
		more frequently than every 30 seconds"""
		if activity_id == self._pending_activity_update:
			return
		self._pending_activity_update = activity_id

		# If we have a pending update already, we have nothing left to do
		if self._pending_activity_update_timer:
			return

		# If there's no pending update, we must not have updated it in the
		# last 30 seconds (except for the initial update, hence we also check
		# for the last update)
		if time.time() - self._last_activity_update > 30:
			self.__update_advertised_current_activity_cb()
			return

		# Otherwise, we start a timer to update the activity at the next
		# interval, which should be 30 seconds from the last update, or if that
		# is in the past already, then now
		next = int(30 - max(0, time.time() - self._last_activity_update))
		self._pending_activity_update_timer = gobject.timeout_add(next * 1000,
				self.__update_advertised_current_activity_cb)
