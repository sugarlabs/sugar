import gobject

from sugar.presence import PresenceService
from sugar.canvas.IconColor import IconColor
import logging

class Friend:
	def __init__(self, buddy):
		self._buddy = buddy
	
	def get_name(self):
		return self._buddy.get_name()

	def get_color(self):
		color = self._buddy.get_color()
		try:
			icolor = IconColor(color)
		except RuntimeError:
			icolor = IconColor()
			logging.info("Buddy %s doesn't have an allowed color; \
						  using a random color instead." % self.get_name())
		return icolor

class FriendsModel(gobject.GObject):
	__gsignals__ = {
		'friend-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						  ([gobject.TYPE_PYOBJECT])),
		'friend-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						  ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		
		self._friends = {}
		
		self._pservice = PresenceService.get_instance()
		self._pservice.connect("buddy-appeared", self.__buddy_appeared_cb)
		self._pservice.connect("buddy-disappeared", self.__buddy_disappeared_cb)

		for buddy in self._pservice.get_buddies():
			self.add_friend(buddy)

	def add_friend(self, buddy):
		friend = Friend(buddy)
		self._friends[buddy.get_name()] = friend
		self.emit('friend-added', friend)

	def remove_friend(self, buddy):
		self.emit('friend-removed', self._friends[buddy.get_name()])
		del self._friends[buddy.get_name()]

	def __iter__(self):
		return self._friends.values().__iter__()

	def __buddy_appeared_cb(self, pservice, buddy):
		self.add_friend(buddy)

	def __buddy_disappeared_cb(self, pservice, buddy):
		self.remove_friend(buddy)
