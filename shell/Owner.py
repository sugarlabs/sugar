import os
import random
import base64

from sugar import env
from sugar.p2p import Stream
from sugar.presence import PresenceService
from sugar import conf
from Friends import Friends

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"

class ShellOwner(object):
	"""Class representing the owner of this machine/instance.  This class
	runs in the shell and serves up the buddy icon and other stuff.  It's the
	server portion of the Owner, paired with the client portion in Buddy.py."""
	def __init__(self):
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
		self._friends = Friends()

	def get_friends(self):
		return self._friends

	def announce(self):
		# Create and announce our presence
		color = conf.get_profile().get_color()
		props = { 'color':  color.get_fill_color() }
		self._service = self._pservice.register_service(self._nick,
				PRESENCE_SERVICE_TYPE, properties=props)
		print "Owner '%s' using port %d" % (self._nick, self._service.get_port())
		self._icon_stream = Stream.Stream.new_from_service(self._service)
		self._icon_stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")

	def _handle_buddy_icon_request(self):
		"""XMLRPC method, return the owner's icon encoded with base64."""
		if self._icon:
			return base64.b64encode(self._icon)
		return ""
