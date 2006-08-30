import gobject

from sugar.canvas.IconColor import IconColor

class Friend:
	def __init__(self, name, color):
		self._name = name
		self._color = color

	def get_name(self):
		return self._name

	def get_color(self):
		return IconColor(self._color)

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

	def has_buddy(self, buddy):
		for friend in self:
			if friend.get_name() == buddy.get_name():
				return True
		return False

	def add_buddy(self, buddy):
		if not self.has_buddy(buddy):	
			friend = Friend(buddy.get_name(), buddy.get_color())
			self._list.append(friend)
			self.emit('friend-added', friend)

	def __iter__(self):
		return self._list.__iter__()
