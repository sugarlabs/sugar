from sugar import env
from sugar.presence import Service
from sugar.presence import Buddy
from sugar.presence import PresenceService
from sugar.p2p import Stream
import os
import random
import base64



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

		# Our presence service
		port = random.randint(40000, 65000)
		properties = {}
		self._service = Service.Service(nick, Buddy.PRESENCE_SERVICE_TYPE,
			domain="", address=None, port=port, properties=properties)
		print "Owner '%s' using port %d" % (nick, port)

		self._icon_stream = Stream.Stream.new_from_service(self._service)
		self._icon_stream.register_reader_handler(self._handle_buddy_icon_request, "get_buddy_icon")

		# Announce ourselves to the world
		self._pservice = PresenceService.PresenceService.get_instance()
		self._pservice.start()
		self._pservice.register_service(self._service)

	def _handle_buddy_icon_request(self):
		"""XMLRPC method, return the owner's icon encoded with base64."""
		if self._icon:
			return base64.b64encode(self._icon)
		return ""

	def set_icon(self, icon):
		"""Can only set icon in constructor for now."""
		pass

