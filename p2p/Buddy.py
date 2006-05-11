import pwd
import os

import Service

class Buddy:
	def __init__(self, service, nick_name):
		self._service = service
		self._nick_name = nick_name
		
	def get_service(self):
		return self._service
		
	def get_nick_name(self):
		return self._nick_name
		
class Owner(Buddy):
	instance = None

	def __init__(self):
		ent = pwd.getpwuid(os.getuid())
		nick = ent[0]
		if not nick or not len(nick):
			nick = "n00b"
		Buddy.__init__(self, None, nick)

	def get_instance():
		if not Owner.instance:
			Owner.instance = Owner()
		return Owner.instance

	get_instance = staticmethod(get_instance)
