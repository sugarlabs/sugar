import os
import random
import base64
import time

import conf
from sugar import env
import logging
from sugar.p2p import Stream
from sugar.presence import PresenceService
from model.Invites import Invites

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class ShellOwner(object):
	"""Class representing the owner of this machine/instance.  This class
	runs in the shell and serves up the buddy icon and other stuff.  It's the
	server portion of the Owner, paired with the client portion in Buddy.py."""
	def __init__(self, shell):
		profile = conf.get_profile()

		self._nick = profile.get_nick_name()
		user_dir = profile.get_path()

		self._icon = None
		for fname in os.listdir(user_dir):
			if not fname.startswith("buddy-icon."):
				continue
			fd = open(os.path.join(user_dir, fname), "r")
			self._icon = fd.read()
			fd.close()
			break

		self._pservice = PresenceService.get_instance()

		self._invites = Invites()

		self._shell = shell
		self._shell.connect('activity-changed', self.__activity_changed_cb)
		self._last_activity_update = time.time()
		self._pending_activity_update_timer = None
		self._pending_activity_update = None

	def get_invites(self):
		return self._invites

	def announce(self):
		# Create and announce our presence
		color = conf.get_profile().get_color()
		props = {'color':color.to_string()}
		activity = self._shell.get_current_activity()
		if activity is not None:
			props['cur_activity':activity.get_id()]
			self._last_activity_update = time.time()
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
		logging.debug("*** Updating current activity to %s" % self._pending_activity_update)
		return False

	def __activity_changed_cb(self, shell, activity):
		"""Update our presence service with the latest activity, but no
		more frequently than every 30 seconds"""
		self._pending_activity_update = activity.get_id()
		# If there's no pending update, we must not have updated it in the
		# last 30 seconds (except for the initial update, hence we also check
		# for the last update)
		if not self._pending_activity_update_timer or time.time() - self._last_activity_update > 30:
			self.__update_advertised_current_activity_cb()
			return

		# If we have a pending update already, we have nothing left to do
		if self._pending_activity_update_timer:
			return

		# Otherwise, we start a timer to update the activity at the next
		# interval, which should be 30 seconds from the last update, or if that
		# is in the past already, then now
		next = 30 - max(30, time.time() - self._last_activity_update)
		self._pending_activity_update_timer = gobject.timeout_add(next * 1000,
				self.__update_advertised_current_activity_cb)
