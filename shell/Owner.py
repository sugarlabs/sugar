import os
import random
import base64

from sugar import env
from sugar.p2p import Stream
from sugar.presence import PresenceService

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class ShellOwner(object):
	"""Class representing the owner of this machine/instance.  This class
	runs in the shell and serves up the buddy icon and other stuff.  It's the
	server portion of the Owner, paired with the client portion in Buddy.py."""
	def __init__(self):
		nick = env.get_nick_name()
		user_dir = env.get_user_dir()
		if not os.path.exists(user_dir):
			try:
				os.makedirs(user_dir)
			except OSError:
				print "Could not create user directory."

		self._icon = None
		for fname in os.listdir(user_dir):
			if not fname.startswith("buddy-icon."):
				continue
			fd = open(os.path.join(user_dir, fname), "r")
			self._icon = fd.read()
			fd.close()
			break

		# Create and announce our presence
		self._pservice = PresenceService.PresenceService()
		self._service = self._pservice.registerService(nick, PRESENCE_SERVICE_TYPE)
		print "Owner '%s' using port %d" % (nick, self._service.get_port())
		self._icon_stream = Stream.Stream.new_from_service(self._service)
		self._icon_stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")

	def _handle_buddy_icon_request(self):
		"""XMLRPC method, return the owner's icon encoded with base64."""
		if self._icon:
			return base64.b64encode(self._icon)
		return ""

	def set_icon(self, icon):
		"""Can only set icon in constructor for now."""
		pass

