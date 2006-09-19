import gobject

class MenuShell(gobject.GObject):
	__gsignals__ = {
		'activated':   (gobject.SIGNAL_RUN_FIRST,
				        gobject.TYPE_NONE, ([])),
		'deactivated': (gobject.SIGNAL_RUN_FIRST,
				        gobject.TYPE_NONE, ([])),
	}

	def __init__(self, grid):
		gobject.GObject.__init__(self)
		self._menu_controller = None
		self._grid = grid

	def is_active(self):
		return (self._menu_controller != None)

	def set_active(self, controller):
		if controller == None:
			self.emit('deactivated')
		else:
			self.emit('activated')

		if self._menu_controller:
			self._menu_controller.popdown()
		self._menu_controller = controller

	def get_grid(self):
		return self._grid
