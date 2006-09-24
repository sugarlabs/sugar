import os
from ConfigParser import ConfigParser

import gobject

from model.BuddyModel import BuddyModel
from sugar import env
import logging

class Friends(gobject.GObject):
	__gsignals__ = {
		'friend-added':   (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([object])),
		'friend-removed': (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([str])),
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._friends = {}
		self._path = os.path.join(env.get_profile_path(), 'friends')

		self.load()

	def has_buddy(self, buddy):
		return self._friends.has_key(buddy.get_name())

	def add_friend(self, buddy_info):
		self._friends[buddy_info.get_name()] = buddy_info
		self.emit('friend-added', buddy_info)

	def make_friend(self, buddy):
		if not self.has_buddy(buddy):	
			self.add_friend(BuddyModel(buddy))
			self.save()

	def remove(self, buddy_info):
		del self._friends[buddy_info.get_name()]
		self.save()
		self.emit('friend-removed', buddy_info.get_name())

	def __iter__(self):
		return self._friends.values().__iter__()

	def load(self):
		cp = ConfigParser()

		try:
			success = cp.read([self._path])
			if success:
				for name in cp.sections():
					buddy = BuddyModel(name)
					self.add_friend(buddy)
		except Exception, exc:
			logging.error("Error parsing friends file: %s" % exc)

	def save(self):
		cp = ConfigParser()

		for friend in self:
			section = friend.get_name()
			cp.add_section(section)
			cp.set(section, 'color', friend.get_color().to_string())

		fileobject = open(self._path, 'w')
		cp.write(fileobject)
		fileobject.close()
