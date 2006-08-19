import gobject

from sugar.presence.PresenceService import PresenceService

class Friend:
	def __init__(self, buddy):
		self._buddy = buddy
	
	def get_name(self):
		return self._buddy.get_name()

class FriendsModel(gobject.GObject):
	__gsignals__ = {
		'friend-added':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						  ([gobject.TYPE_PYOBJECT])),
		'friend-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						  ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		
		self._friends = []
		
		self._pservice = PresenceService()
		self._pservice.connect("buddy-appeared", self.__buddy_appeared_cb)

		for buddy in self._pservice.get_buddies():
			self.add_friend(buddy)

	def add_friend(self, buddy):
		friend = Friend(buddy)
		self._friends.append(friend)
		self.emit('friend-added', friend)

	def __iter__(self):
		return self._friends.__iter__()

	def __buddy_appeared_cb(self, pservice, buddy):
		self.add_friend(buddy)
