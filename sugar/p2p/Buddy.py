import pwd
import os

from Service import Service
from sugar import env

PRESENCE_SERVICE_TYPE = "_olpc_presence._tcp"
PRESENCE_SERVICE_PORT = 6000

__buddy_service_types = [PRESENCE_SERVICE_TYPE]

def recognize_buddy_service_type(stype):
	if stype not in __buddy_service_types:
		__buddy_service_types.append(stype)

def get_recognized_buddy_service_types():
	return __buddy_service_types[:]


class Buddy(object):
	def __init__(self, service):
		self._services = {}
		self._services[service.get_type()] = service
		self._nick_name = service.get_name()
		self._address = service.get_address()

	def get_icon(self):
		"""Return the buddies icon, if any."""
		return self._icon
		
	def get_address(self):
		return self._address

	def add_service(self, service):
		if service.get_name() != self._nick_name:
			return False
		if service.get_address() != self._address:
			return False
		if self._services.has_key(service.get_type()):
			return False
		self._services[service.get_type()] = service

	def remove_service(self, stype):
		if self._services.has_key(stype):
			del self._services[stype]

	def get_service(self, stype):
		if self._services.has_key(stype):
			return self._services[stype]
		return None
		
	def get_nick_name(self):
		return self._nick_name

	def set_icon(self, icon):
		"""Can only set icon for other buddies.  The Owner
		takes care of setting it's own icon."""
		self._icon = icon
		

class Owner(Buddy):
	"""Class representing the owner of this machine/instance."""
	def __init__(self, group):
		self._group = group
	
		nick = pwd.getpwuid(os.getuid())[0]
		if not nick or not len(nick):
			nick = "n00b"

		self._presence_service = Service(nick, PRESENCE_SERVICE_TYPE, PRESENCE_SERVICE_PORT)
		Buddy.__init__(self, self._presence_service)

		for fname in os.listdir(env.get_user_dir()):
			if not fname.startswith("buddy-icon."):
				continue
			fd = open(os.path.join(env.get_user_dir(), fname), "r")
			self._icon = fd.read()
			fd.close()
			break

	def set_icon(self, icon):
		"""Can only set icon in constructor for now."""
		pass
		
	def register(self):
		self._presence_service.register(self._group)
