import pwd
import os

from Service import Service

PRESENCE_SERVICE_TYPE = "_olpc_presence._tcp"
PRESENCE_SERVICE_PORT = 6000

class Buddy:
	def __init__(self, service, nick_name):
		self._service = service
		self._nick_name = nick_name
		
	def get_service_name(self):
		return self._service.get_name()
		
	def get_nick_name(self):
		return self._nick_name
		
class Owner(Buddy):
	def __init__(self, group):
		self._group = group
	
		nick = pwd.getpwuid(os.getuid())[0]
		if not nick or not len(nick):
			nick = "n00b"

		service = Service(nick, PRESENCE_SERVICE_TYPE,
						  PRESENCE_SERVICE_PORT)

		Buddy.__init__(self, service, nick)
		
	def register(self):
		self._service.register(self._group)
