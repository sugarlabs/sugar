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
		'enter-edge':    (gobject.SIGNAL_RUN_FIRST,
				          gobject.TYPE_NONE, ([])),
		'enter-corner':  (gobject.SIGNAL_RUN_FIRST,
				          gobject.TYPE_NONE, ([])),
		'leave':		 (gobject.SIGNAL_RUN_FIRST,
				          gobject.TYPE_NONE, ([]))
	}

	HOVER_NONE = 0
	HOVER_CORNER = 1
	HOVER_EDGE = 2

	def __init__(self):
		gobject.GObject.__init__(self)

		self._windows = []
		self._hover = EventFrame.HOVER_NONE
		self._active = False

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
		invisible.connect('motion-notify-event', self._motion_notify_cb)
		invisible.connect('leave-notify-event', self._leave_notify_cb)

		invisible.realize()
		invisible.window.set_events(gtk.gdk.POINTER_MOTION_MASK |
									gtk.gdk.LEAVE_NOTIFY_MASK)
		invisible.window.move_resize(x, y, width, height)

		return invisible

	def _motion_notify_cb(self, widget, event):
		screen_w = gtk.gdk.screen_width()
		screen_h = gtk.gdk.screen_height()

		if (event.x == 0 and event.y == 0) or \
		   (event.x == 0 and event.y == screen_h - 1) or \
		   (event.x == screen_w - 1 and event.y == 0) or \
		   (event.x == screen_w - 1 and event.y == screen_h - 1):
			if self._hover != EventFrame.HOVER_CORNER:
				self._hover = EventFrame.HOVER_CORNER
				self.emit('enter-corner')
		else:
			if self._hover != EventFrame.HOVER_EDGE:
				self._hover = EventFrame.HOVER_EDGE
				self.emit('enter-edge')

	def _leave_notify_cb(self, widget, event):
		self._hover = EventFrame.HOVER_NONE
		if self._active:
			self.emit('leave')

	def show(self):
		self._active = True
		for window in self._windows:
			window.show()

	def hide(self):
		self._active = False
		for window in self._windows:
			window.hide()

	def _active_window_changed_cb(self, screen):
		for window in self._windows:
			window.window.raise_()

class Frame:
	INACTIVE = 0
	TEMPORARY = 1
	STICKY = 2
	HIDE_ON_LEAVE = 3
	AUTOMATIC = 4

	def __init__(self, shell):
		self._windows = []
		self._shell = shell
		self._mode = Frame.INACTIVE

		self._timeline = Timeline(self)
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
		self._event_frame.connect('enter-edge', self._enter_edge_cb)
		self._event_frame.connect('enter-corner', self._enter_corner_cb)
		self._event_frame.connect('leave', self._event_frame_leave_cb)
		self._event_frame.show()

	def _add_panel(self, model, x, y, width, height):
		grid = self._shell.get_grid()

		panel_window = PanelWindow(grid, model, x, y, width, height)
		panel_window.connect('enter-notify-event', self._enter_notify_cb)
		panel_window.connect('leave-notify-event', self._leave_notify_cb)

		self._windows.append(panel_window)

	def _menu_shell_activated_cb(self, menu_shell):
		self._timeline.goto('slide_in', True)

	def _menu_shell_deactivated_cb(self, menu_shell):
		if self._mode != Frame.STICKY:
			self._timeline.play('before_slide_out', 'slide_out')

	def _enter_notify_cb(self, window, event):
		self._timeline.goto('slide_in', True)

	def _leave_notify_cb(self, window, event):
		# FIXME for some reason every click cause also a leave-notify
		if event.state == gtk.gdk.BUTTON1_MASK:
			return

		if not self._menu_shell.is_active() and \
			   self._mode == Frame.HIDE_ON_LEAVE:
			self._timeline.play('before_slide_out', 'slide_out')

	def _enter_edge_cb(self, event_frame):
		self._mode = Frame.HIDE_ON_LEAVE
		self._timeline.play(None, 'slide_in')

	def _enter_corner_cb(self, event_frame):
		self._mode = Frame.HIDE_ON_LEAVE
		self._timeline.play('slide_in', 'slide_in')

	def _event_frame_leave_cb(self, event_frame):
		if self._mode != Frame.STICKY:
			self._timeline.goto('slide_out', True)

	def show_and_hide(self, seconds):
		self._mode = Frame.AUTOMATIC
		self._timeline.play()

	def notify_key_press(self):
		if self._timeline.on_tag('slide_in'):
			self._timeline.play('before_slide_out', 'slide_out')
		elif self._timeline.on_tag('before_slide_out'):
			self._mode = Frame.TEMPORARY
		else:
			self._mode = Frame.STICKY
			self._timeline.play('slide_in', 'slide_in')

	def notify_key_release(self):
		if self._mode == Frame.TEMPORARY:
			self._timeline.play('before_slide_out', 'slide_out')

	def do_slide_in(self, current=0, n_frames=0):
		if not self._windows[0].props.visible:
			for panel in self._windows:
				panel.show()
			self._event_frame.hide()

	def do_slide_out(self, current=0, n_frames=0):
		if self._windows[0].props.visible:
			for panel in self._windows:
				panel.hide()
			self._event_frame.show()

	def is_visible(self):
		if self._windows[0].props.visible:
			return True
		return False
