import gtk
import gobject
import goocanvas
import wnck

from view.frame.BottomPanel import BottomPanel
from view.frame.RightPanel import RightPanel
from view.frame.TopPanel import TopPanel
from view.frame.PanelWindow import PanelWindow
from sugar.canvas.Grid import Grid
from sugar.canvas.MenuShell import MenuShell

class EventFrame(gobject.GObject):
	__gsignals__ = {
		'hover':  (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([])),
	}
	def __init__(self):
		gobject.GObject.__init__(self)

		self._windows = []

		invisible = self._create_invisible(0, 0, gtk.gdk.screen_width(), 1)
		self._windows.append(invisible)

		invisible = self._create_invisible(0, 0, 1, gtk.gdk.screen_height())
		self._windows.append(invisible)

		invisible = self._create_invisible(gtk.gdk.screen_width() - 1, 0,
										   gtk.gdk.screen_width(),
										   gtk.gdk.screen_height())
		self._windows.append(invisible)

		invisible = self._create_invisible(0, gtk.gdk.screen_height() - 1,
										   gtk.gdk.screen_width(),
										   gtk.gdk.screen_height())
		self._windows.append(invisible)

		screen = wnck.screen_get_default()
		screen.connect('active-window-changed',
					   self._active_window_changed_cb)

	def _create_invisible(self, x, y, width, height):
		invisible = gtk.Invisible()
		invisible.connect('enter-notify-event', self._enter_notify_cb)

		invisible.realize()
		invisible.window.set_events(gtk.gdk.ENTER_NOTIFY_MASK)
		invisible.window.move_resize(x, y, width, height)

		return invisible

	def _enter_notify_cb(self, widget, event):
		self.emit('hover')

	def show(self):
		for window in self._windows:
			window.show()

	def hide(self):
		for window in self._windows:
			window.hide()

	def _active_window_changed_cb(self, screen):
		for window in self._windows:
			window.window.raise_()

class Frame:
	def __init__(self, shell):
		self._windows = []
		self._shell = shell
		self._hide_timeout = 0

		model = goocanvas.CanvasModelSimple()
		root = model.get_root_item()

		grid = shell.get_grid()
		menu_shell = MenuShell(grid)

		bg = goocanvas.Rect(fill_color="#4f4f4f", line_width=0)
		grid.set_constraints(bg, 0, 0, 80, 60)
		root.add_child(bg)

		panel = BottomPanel(shell)
		grid.set_constraints(panel, 5, 55)
		root.add_child(panel)

		self._add_panel(model, 0, 55, 80, 5)

		panel = TopPanel(shell, menu_shell)
		root.add_child(panel)

		self._add_panel(model, 0, 0, 80, 5)
		
		panel = RightPanel(shell, menu_shell)
		grid.set_constraints(panel, 75, 5)
		root.add_child(panel)

		self._add_panel(model, 75, 5, 5, 50)

		self._add_panel(model, 0, 5, 5, 50)

		self._event_frame = EventFrame()
		self._event_frame.connect('hover', self._event_frame_hover_cb)
		self._event_frame.show()

	def _add_panel(self, model, x, y, width, height):
		grid = self._shell.get_grid()

		panel_window = PanelWindow(grid, model, x, y, width, height)
		panel_window.connect('enter-notify-event', self._enter_notify_cb)
		panel_window.connect('leave-notify-event', self._leave_notify_cb)

		self._windows.append(panel_window)

	def _enter_notify_cb(self, window, event):
		self._cancel_hide()

	def _leave_notify_cb(self, window, event):
		# FIXME for some reason every click cause also a leave-notify
		if event.state == gtk.gdk.BUTTON1_MASK:
			return

		self._hide_after(500)

	def _event_frame_hover_cb(self, event_frame):
		self.show()

	def _hide_timeout_cb(self):
		self.hide()
		return False

	def _cancel_hide(self):
		if self._hide_timeout > 0:
			gobject.source_remove(self._hide_timeout)

	def _hide_after(self, ms):
		self._cancel_hide()
		self._hide_timeout = gobject.timeout_add(ms, self._hide_timeout_cb)

	def show_and_hide(self, seconds):
		self.show()
		self._hide_after(seconds * 1000)

	def show(self):
		for panel in self._windows:
			panel.show()
		self._event_frame.hide()

	def hide(self):
		for panel in self._windows:
			panel.hide()
		self._event_frame.show()

	def toggle_visibility(self):
		if self._windows[0].props.visible:
			self.hide()
		else:
			self.show()
