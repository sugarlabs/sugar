# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
			self.add_friend(BuddyModel(buddy=buddy))
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
