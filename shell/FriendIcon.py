from sugar.canvas.IconItem import IconItem
from FriendPopup import FriendPopup
from sugar.canvas.Grid import Grid

class _PopupShell:
	def __init__(self):
		self._popup_controller = None

	def set_active(self, controller):
		if self._popup_controller:
			self._popup_controller._popdown()
		self._popup_controller = controller

class FriendIcon(IconItem):
	_popup_shell = _PopupShell()

	def __init__(self, shell, friend):
		IconItem.__init__(self, icon_name='stock-buddy',
						  color=friend.get_color(), size=96)

		self._shell = shell
		self._friend = friend
		self._popup = None
		self._popup_distance = 0
		self._hover_popup = False
		self._popdown_on_leave = False

		self.connect('popup', self._popup_cb)
		self.connect('popdown', self._popdown_cb)

	def set_popup_distance(self, distance):
		self._popup_distance = distance

	def get_friend(self):
		return self._friend

	def _popdown(self):
		if self._popup:
			self._popup.destroy()
			self._popup = None

	def _popup_cb(self, icon, x1, y1, x2, y2):
		self._popdown()

		FriendIcon._popup_shell.set_active(None)

		grid = Grid()
		self._popup = FriendPopup(self._shell, grid, icon.get_friend())
		self._popup.connect('enter-notify-event',
							self._popup_enter_notify_event_cb)
		self._popup.connect('leave-notify-event',
							self._popup_leave_notify_event_cb)

		distance = self._popup_distance

		[grid_x1, grid_y1] = grid.convert_from_screen(x1, y1)
		[grid_x2, grid_y2] = grid.convert_from_screen(x2, y2)

		if grid_x2 + self._popup.get_width() + distance > Grid.ROWS:
			grid_x = grid_x1 - self._popup.get_width() - distance
		else:
			grid_x = grid_x2 + distance

		grid_y = grid_y1

		if grid_y < 0:
			grid_y = 0
		if grid_y + self._popup.get_width() > Grid.ROWS:
			grid_y = Grid.ROWS - self._popup.get_width()

		grid.set_constraints(self._popup, grid_x, grid_y,
							 self._popup.get_width(), self._popup.get_height())

		self._popup.show()

		FriendIcon._popup_shell.set_active(self)

	def _popdown_cb(self, friend):
		if not self._hover_popup:
			self._popdown()

	def _popup_enter_notify_event_cb(self, widget, event):
		self._hover_popup = True

	def _popup_leave_notify_event_cb(self, widget, event):
		self._hover_popup = False
		if self._popdown_on_leave:
			self._popdown()
