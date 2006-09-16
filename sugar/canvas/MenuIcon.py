from sugar.canvas.IconItem import IconItem
from sugar.canvas.Grid import Grid

class _MenuShell:
	def __init__(self):
		self._menu_controller = None

	def set_active(self, controller):
		if self._menu_controller:
			self._menu_controller.popdown()
		self._menu_controller = controller

class MenuIcon(IconItem):
	_menu_shell = _MenuShell()

	def __init__(self, grid, **kwargs):
		IconItem.__init__(self, **kwargs)

		self._grid = grid
		self._menu = None
		self._menu_distance = 0
		self._hover_menu = False
		self._popdown_on_leave = False

		self.connect('popup', self._popup_cb)
		self.connect('popdown', self._popdown_cb)

	def set_menu_distance(self, distance):
		self._menu_distance = distance

	def popdown(self):
		if self._menu:
			self._menu.destroy()
			self._menu = None

	def _popup_cb(self, icon, x1, y1, x2, y2):
		self.popdown()

		MenuIcon._menu_shell.set_active(None)

		grid = self._shell.get_grid()
		self._menu = self.create_menu()
		self._menu.connect('enter-notify-event',
						   self._menu_enter_notify_event_cb)
		self._menu.connect('leave-notify-event',
						   self._menu_leave_notify_event_cb)

		distance = self._menu_distance

		[grid_x1, grid_y1] = grid.convert_from_screen(x1, y1)
		[grid_x2, grid_y2] = grid.convert_from_screen(x2, y2)

		grid_x = grid_x2 + distance
		if grid_x + self._menu.get_width() > Grid.ROWS:
			grid_x = grid_x1 - self._menu.get_width() + 1 - distance

		grid_y = grid_y1

		if grid_y < 0:
			grid_y = 0
		if grid_y + self._menu.get_width() > Grid.ROWS:
			grid_y = Grid.ROWS - self._menu.get_width()

		grid.set_constraints(self._menu, grid_x, grid_y,
							 self._menu.get_width(), self._menu.get_height())

		self._menu.show()

		MenuIcon._menu_shell.set_active(self)

	def _popdown_cb(self, friend):
		if not self._hover_menu:
			self.popdown()
		else:
			self._popdown_on_leave = True

	def _menu_enter_notify_event_cb(self, widget, event):
		self._hover_menu = True

	def _menu_leave_notify_event_cb(self, widget, event):
		self._hover_menu = False
		if self._popdown_on_leave:
			self.popdown()
