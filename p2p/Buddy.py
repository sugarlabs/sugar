import pwd
import os

from Service import *
import presence

BUDDY_SERVICE_TYPE = "_olpc_buddy._tcp"
BUDDY_SERVICE_PORT = 666

GROUP_SERVICE_TYPE = "_olpc_buddy._udp"
GROUP_SERVICE_PORT = 6666

class Buddy:
	def __init__(self, service, nick_name):
		self._service = service
		self._nick_name = nick_name
		
	def get_service(self):
		return self._service

	def get_service_name(self):
		return self._service.get_name()
		
	def get_nick_name(self):
		return self._nick_name
		
class Owner(Buddy):
	def __init__(self):
		ent = pwd.getpwuid(os.getuid())
		nick = ent[0]
		if not nick or not len(nick):
			nick = "n00b"

		service = Service(nick, '', '', GROUP_SERVICE_PORT)

		Buddy.__init__(self, service, nick)
		
	def register(self):
		pannounce = presence.PresenceAnnounce()
		pannounce.register_service(self._nick_name,
								   BUDDY_SERVICE_PORT,
								   BUDDY_SERVICE_TYPE,
								   nickname = self._nick_name)
