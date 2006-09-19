import goocanvas
import gobject

from sugar.canvas.IconItem import IconItem
from sugar.canvas.Grid import Grid

class _MenuStrategy:
	def get_menu_position(self, menu, grid_x1, grid_y1, grid_x2, grid_y2):
		grid_x = grid_x2
		if grid_x + menu.get_width() > Grid.COLS:
			grid_x = grid_x1 - menu.get_width() + 1

		grid_y = grid_y1

		if grid_y < 0:
			grid_y = 0
		if grid_y + menu.get_width() > Grid.ROWS:
			grid_y = Grid.ROWS - menu.get_width()

		return [grid_x, grid_y]

class MenuIcon(IconItem, goocanvas.Item):
	def __init__(self, menu_shell, **kwargs):
		IconItem.__init__(self, **kwargs)

		self._menu_shell = menu_shell
		self._grid = menu_shell.get_grid()
		self._menu = None
		self._hover_menu = False
		self._popdown_on_leave = False
		self._popdown_sid = 0
		self._menu_strategy = _MenuStrategy()

	def popdown(self):
		if self._menu:
			self._menu.destroy()
			self._menu = None
			self._menu_shell.set_active(None)

	def set_menu_strategy(self, strategy):
		self._menu_strategy = strategy

	def _popup(self, x1, y1, x2, y2):
		self.popdown()

		self._menu_shell.set_active(None)

		grid = self._shell.get_grid()
		self._menu = self.create_menu()
		self._menu.connect('enter-notify-event',
						   self._menu_enter_notify_event_cb)
		self._menu.connect('leave-notify-event',
						   self._menu_leave_notify_event_cb)

		[grid_x1, grid_y1] = grid.convert_from_screen(x1, y1)
		[grid_x2, grid_y2] = grid.convert_from_screen(x2, y2)

		strategy = self._menu_strategy
		[grid_x, grid_y] = strategy.get_menu_position(self._menu,
													  grid_x1, grid_y1,
												      grid_x2, grid_y2)

		grid.set_constraints(self._menu, grid_x, grid_y,
							 self._menu.get_width(), self._menu.get_height())

		self._menu.show()

		self._menu_shell.set_active(self)

	def _menu_enter_notify_event_cb(self, widget, event):
		self._hover_menu = True

	def _menu_leave_notify_event_cb(self, widget, event):
		self._hover_menu = False
		if self._popdown_on_leave:
			self.popdown()

	def do_create_view(self, canvas, parent_view):
		view = IconItem.do_create_view(self, canvas, parent_view)
		view.connect('enter-notify-event', self._enter_notify_event_cb, canvas)
		view.connect('leave-notify-event', self._leave_notify_event_cb)
		return view

	def _start_popdown_timeout(self):
		self._stop_popdown_timeout()
		self._popdown_sid = gobject.timeout_add(1000, self._popdown_timeout_cb)

	def _stop_popdown_timeout(self):
		if self._popdown_sid > 0:
			gobject.source_remove(self._popdown_sid)
			self._popdown_sid = 0

	def _enter_notify_event_cb(self, view, target, event, canvas):
		self._stop_popdown_timeout()

		[x1, y1] = canvas.convert_to_pixels(view.get_bounds().x1,
								 		    view.get_bounds().y1)
		[x2, y2] = canvas.convert_to_pixels(view.get_bounds().x2,
								 		    view.get_bounds().y2)

		[window_x, window_y] = canvas.window.get_origin()

		x1 += window_x
		y1 += window_y
		x2 += window_x
		y2 += window_y

		self._popup(int(x1), int(y1), int(x2), int(y2))

	def _popdown_timeout_cb(self):
		self._popdown_sid = 0

		if not self._hover_menu:
			self.popdown()
		else:
			self._popdown_on_leave = True

		return False

	def _leave_notify_event_cb(self, view, target, event):
		self._start_popdown_timeout()
