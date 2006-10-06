import hippo
import gobject

from sugar.graphics.canvasicon import CanvasIcon

class _MenuStrategy:
	def get_menu_position(self, menu, item):
		return item.get_context().translate_to_widget(item)

class MenuIcon(CanvasIcon):
	def __init__(self, menu_shell, **kwargs):
		CanvasIcon.__init__(self, **kwargs)

		self._menu_shell = menu_shell
		self._menu = None
		self._hover_menu = False
		self._popdown_on_leave = False
		self._popdown_sid = 0
		self._menu_strategy = _MenuStrategy()

		self.connect('motion-notify-event', self._motion_notify_event_cb)

	def popdown(self):
		if self._menu:
			self._menu.destroy()
			self._menu = None
			self._menu_shell.set_active(None)

	def set_menu_strategy(self, strategy):
		self._menu_strategy = strategy

	def _popup(self):
		self.popdown()

		self._menu_shell.set_active(None)

		self._menu = self.create_menu()
		self._menu.connect('enter-notify-event',
						   self._menu_enter_notify_event_cb)
		self._menu.connect('leave-notify-event',
						   self._menu_leave_notify_event_cb)

		strategy = self._menu_strategy
		[x, y] = strategy.get_menu_position(self._menu, self)

		self._menu.move(x, y)
		self._menu.show()

		self._menu_shell.set_active(self)

	def _menu_enter_notify_event_cb(self, widget, event):
		self._hover_menu = True

	def _menu_leave_notify_event_cb(self, widget, event):
		self._hover_menu = False
		if self._popdown_on_leave:
			self.popdown()

	def _start_popdown_timeout(self):
		self._stop_popdown_timeout()
		self._popdown_sid = gobject.timeout_add(1000, self._popdown_timeout_cb)

	def _stop_popdown_timeout(self):
		if self._popdown_sid > 0:
			gobject.source_remove(self._popdown_sid)
			self._popdown_sid = 0

	def _motion_notify_event_cb(self, item, event):
		if event.detail == hippo.MOTION_DETAIL_ENTER:
			self._motion_notify_enter()
		elif event.detail == hippo.MOTION_DETAIL_LEAVE:
			self._motion_notify_leave()

	def _motion_notify_enter(self):
		self._stop_popdown_timeout()
		self._popup()

	def _motion_notify_leave(self):
		self._start_popdown_timeout()

	def _popdown_timeout_cb(self):
		self._popdown_sid = 0

		if not self._hover_menu:
			self.popdown()
		else:
			self._popdown_on_leave = True

		return False
