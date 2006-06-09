import pwd
import os

import pygtk
pygtk.require('2.0')
import gtk


#from sugar import env

PRESENCE_SERVICE_TYPE = "_presence_olpc._tcp"


class Buddy(object):
	"""Represents another person on the network and keeps track of the
	activities and resources they make available for sharing."""
	def __init__(self, service):
		self._services = {}
		self._nick_name = service.get_name()
		self._address = service.get_address()
		self._valid = False
		self._icon = None
		self.add_service(service)

	def add_service(self, service):
		"""Adds a new service to this buddy's service list."""
		if service.get_type() in self._services.keys():
			return
		self._services.keys[service.get_type()] = service
		# FIXME: send out signal for new service found
		if service.get_type() == PRESENCE_SERVICE_TYPE:
			# A buddy isn't valid until its official presence
			# service has been found and resolved
			self._valid = True

	def remove_service(self, service):
		"""Remove a service from a buddy; ie, the activity was closed
		or the buddy went away."""
		if service.get_type() in self._services.keys():
			del self._services[service.get_type()]
		if service.get_type() == PRESENCE_SERVICE_TYPE:
			self._valid = False

	def is_valid(self):
		"""Return whether the buddy is valid or not.  A buddy is
		not valid until its official presence service has been found
		and successfully resolved."""
		return self._valid

	def get_icon_pixbuf(self):
		if self._icon:
			pbl = gtk.gdk.PixbufLoader()
			pbl.write(self._icon)
			pbl.close()
			return pbl.get_pixbuf()
		else:
			return None

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
		# FIXME: do callbacks for icon-changed
		

class Owner(Buddy):
	"""Class representing the owner of this machine/instance."""
	def __init__(self):
		nick = env.get_nick_name()
		if not nick:
			nick = pwd.getpwuid(os.getuid())[0]
		if not nick or not len(nick):
			nick = "n00b"

		Buddy.__init__(self)

		user_dir = env.get_user_dir()
		if not os.path.exists(user_dir):
			try:
				os.makedirs(user_dir)
			except OSError:
				print 'Could not create user directory.'

		for fname in os.listdir(user_dir):
			if not fname.startswith("buddy-icon."):
				continue
			fd = open(os.path.join(user_dir, fname), "r")
			self._icon = fd.read()
			fd.close()
			break

	def set_icon(self, icon):
		"""Can only set icon in constructor for now."""
		pass
		
	def add_service(self, service):
		"""Do nothing here, since all services we need to know about
		are registered with us by our group."""
		pass
