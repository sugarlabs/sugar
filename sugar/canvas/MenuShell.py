class MenuShell:
	def __init__(self, grid):
		self._menu_controller = None
		self._grid = grid

	def set_active(self, controller):
		if self._menu_controller:
			self._menu_controller.popdown()
		self._menu_controller = controller

	def get_grid(self):
		return self._grid
