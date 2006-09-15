import os
from ConfigParser import ConfigParser

import gobject

from sugar.canvas.IconColor import IconColor
from sugar.presence import PresenceService
from sugar import env

class Friend:
	def __init__(self, name, color):
		self._name = name
		self._color = color

	def get_name(self):
		return self._name

	def get_color(self):
		return IconColor(self._color)

	def get_buddy(self):
		pservice = PresenceService.get_instance()
		return pservice.get_buddy_by_name(self._name)

class Friends(gobject.GObject):
	__gsignals__ = {
		'friend-added':   (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([object])),
		'friend-removed': (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([object])),
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._list = []
		self._path = os.path.join(env.get_profile_path(), 'friends')

		self.load()

	def has_buddy(self, buddy):
		for friend in self:
			if friend.get_name() == buddy.get_name():
				return True
		return False

	def add_friend(self, name, color):
		friend = Friend(name, color)
		self._list.append(friend)

		self.emit('friend-added', friend)

	def add_buddy(self, buddy):
		if not self.has_buddy(buddy):	
			self.add_friend(buddy.get_name(), buddy.get_color())
			self.save()

	def __iter__(self):
		return self._list.__iter__()

	def load(self):
		cp = ConfigParser()

		if cp.read([self._path]):
			for name in cp.sections():
				self.add_friend(name, cp.get(name, 'color'))

	def save(self):
		cp = ConfigParser()

		for friend in self:
			section = friend.get_name()
			cp.add_section(section)
			cp.set(section, 'color', friend.get_color().to_string())

		fileobject = open(self._path, 'w')
		cp.write(fileobject)
		fileobject.close()
