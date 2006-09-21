import gtk
import gobject
import goocanvas
import wnck

from view.frame.BottomPanel import BottomPanel
from view.frame.RightPanel import RightPanel
from view.frame.TopPanel import TopPanel
from view.frame.PanelWindow import PanelWindow
from sugar.canvas.Grid import Grid
from sugar.canvas.Timeline import Timeline
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
		self._sticky = False

		self._timeline = Timeline(self)
		self._timeline.add_tag('start', 0, 0)
		self._timeline.add_tag('slide_in', 6, 12)
		self._timeline.add_tag('before_slide_out', 36, 36)
		self._timeline.add_tag('slide_out', 37, 42)

		model = goocanvas.CanvasModelSimple()
		root = model.get_root_item()

		grid = shell.get_grid()
		self._menu_shell = MenuShell(grid)
		self._menu_shell.connect('activated', self._menu_shell_activated_cb)
		self._menu_shell.connect('deactivated', self._menu_shell_deactivated_cb)

		bg = goocanvas.Rect(fill_color="#4f4f4f", line_width=0)
		grid.set_constraints(bg, 0, 0, 80, 60)
		root.add_child(bg)

		panel = BottomPanel(shell)
		grid.set_constraints(panel, 5, 55)
		root.add_child(panel)

		self._add_panel(model, 0, 55, 80, 5)

		panel = TopPanel(shell, self._menu_shell)
		root.add_child(panel)

		self._add_panel(model, 0, 0, 80, 5)
		
		panel = RightPanel(shell, self._menu_shell)
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

	def _menu_shell_activated_cb(self, menu_shell):
		pass

	def _menu_shell_deactivated_cb(self, menu_shell):
		pass

	def _enter_notify_cb(self, window, event):
		pass

	def _leave_notify_cb(self, window, event):
		pass

	def _event_frame_hover_cb(self, event_frame):
		pass

	def show_and_hide(self, seconds):
		self._timeline.play()

	def notify_key_press(self):
		if self._timeline.on_tag('slide_in'):
			self._timeline.play('before_slide_out', 'slide_out')
		elif self._timeline.on_tag('before_slide_out'):
			self._sticky = True
		else:
			self._sticky = False
			self._timeline.play('slide_in', 'slide_in')

	def notify_key_release(self):
		if self._sticky:
			self._timeline.play('before_slide_out', 'slide_out')

	def do_slide_in(self, current, n_frames):
		if current == 0:
			for panel in self._windows:
				panel.show()
			self._event_frame.hide()

	def do_slide_out(self, current, n_frames):
		if current == 0:
			for panel in self._windows:
				panel.hide()
			self._event_frame.show()
