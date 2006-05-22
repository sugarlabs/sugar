import pwd
import os

from Service import Service

PRESENCE_SERVICE_TYPE = "_olpc_presence._tcp"
PRESENCE_SERVICE_PORT = 6000

class BuddyBase:
	def __init__(self, service, nick_name):
		self._service = service
		self._nick_name = nick_name

	def get_icon(self):
		"""Return the buddies icon, if any."""
		return self._icon
		
	def get_address(self):
		return self._service.get_address()

	def get_service_name(self):
		return self._service.get_name()
		
	def get_nick_name(self):
		return self._nick_name
		
class Buddy(BuddyBase):
	"""Normal buddy class."""

	def set_icon(self, icon):
		"""Can only set icon for other buddies.  The Owner
		takes care of setting it's own icon."""
		self._icon = icon
	

class Owner(BuddyBase):
	"""Class representing the owner of this machine/instance."""
	def __init__(self, group):
		self._group = group
	
		nick = pwd.getpwuid(os.getuid())[0]
		if not nick or not len(nick):
			nick = "n00b"

		service = Service(nick, PRESENCE_SERVICE_TYPE, PRESENCE_SERVICE_PORT)
		BuddyBase.__init__(self, service, nick)

		sugar_dir = os.path.abspath(os.path.expanduser("~/.sugar"))
		icon = None
		for fname in os.listdir(sugar_dir):
			if not fname.startswith("buddy-icon."):
				continue
			fd = open(os.path.join(sugar_dir, fname), "r")
			self._icon = fd.read()
			fd.close()
			break

		
	def register(self):
		self._service.register(self._group)
