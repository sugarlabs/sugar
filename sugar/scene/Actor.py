import gobject

from sugar.scene.Transformation import Transformation

class Actor(gobject.GObject):
	__gsignals__ = {
		'changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ())
	}

	def __init__(self):
		gobject.GObject.__init__(self)

		self._parent = None
		self._x = 0
		self._y = 0
		self._width = -1
		self._height = -1
		self._transf = Transformation()

	def set_position(self, x, y):
		self._x = x
		self._y = y
		self.notify_changed()

	def _get_parents(self):
		parents = []
		parent = self._parent
		while parent:
			parents.insert(0, parent)
			parent = parent._parent
		return parents

	def _get_abs_position(self, x, y):
		transf = None
		parents = self._get_parents()
		for actor in parents:
			if transf:
				transf = transf.compose(actor._transf)
			else:
				transf = actor._transf
		return transf.get_position(x, y)

	def notify_changed(self):
		if self._parent:
			self._parent.notify_changed()
		else:
			self.emit('changed')

	def set_size(self, width, height):
		self._width = width
		self._height = height
		self.notify_changed()

	def render(self, drawable):
		pass
