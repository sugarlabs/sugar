# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import gobject
import hippo
import wnck

from view.frame.ActivitiesBox import ActivitiesBox
from view.frame.ZoomBox import ZoomBox
from view.frame.FriendsBox import FriendsBox
from view.frame.PanelWindow import PanelWindow
from view.frame.notificationtray import NotificationTray
from sugar.graphics.timeline import Timeline
from sugar.graphics.menushell import MenuShell
from sugar.graphics.grid import Grid

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
		invisible.connect('enter-notify-event', self._enter_notify_cb)
		invisible.connect('leave-notify-event', self._leave_notify_cb)

		invisible.realize()
		invisible.window.set_events(gtk.gdk.POINTER_MOTION_MASK |
									gtk.gdk.ENTER_NOTIFY_MASK |
									gtk.gdk.LEAVE_NOTIFY_MASK)
		invisible.window.move_resize(x, y, width, height)

		return invisible

	def _enter_notify_cb(self, widget, event):
		self._notify_enter(event.x, event.y)

	def _motion_notify_cb(self, widget, event):
		self._notify_enter(event.x, event.y)

	def _notify_enter(self, x, y):
		screen_w = gtk.gdk.screen_width()
		screen_h = gtk.gdk.screen_height()

		if (x == 0 and y == 0) or \
		   (x == 0 and y == screen_h - 1) or \
		   (x == screen_w - 1 and y == 0) or \
		   (x == screen_w - 1 and y == screen_h - 1):
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

		self._event_frame = EventFrame()
		self._event_frame.connect('enter-edge', self._enter_edge_cb)
		self._event_frame.connect('enter-corner', self._enter_corner_cb)
		self._event_frame.connect('leave', self._event_frame_leave_cb)
		self._event_frame.show()

		grid = Grid()

		self._menu_shell = MenuShell()
		self._menu_shell.connect('activated', self._menu_shell_activated_cb)
		self._menu_shell.connect('deactivated', self._menu_shell_deactivated_cb)

		top_panel = self._create_panel(grid, 0, 0, 16, 1)

		box = ZoomBox(self._shell, self._menu_shell)

		[x, y] = grid.point(1, 0)
		top_panel.append(box, hippo.PACK_FIXED)
		top_panel.move(box, x, y)

		tray = NotificationTray()
		tray_box = hippo.CanvasBox(box_width=grid.dimension(1),
								   box_height=grid.dimension(1),
								   xalign=hippo.ALIGNMENT_END)

		tray_widget = hippo.CanvasWidget()
		tray_widget.props.widget = tray
		tray_box.append(tray_widget, gtk.EXPAND)

		[x, y] = grid.point(14, 0)
		top_panel.append(tray_box, hippo.PACK_FIXED)
		top_panel.move(tray_box, x, y)

		bottom_panel = self._create_panel(grid, 0, 11, 16, 1)

		box = ActivitiesBox(self._shell)
		bottom_panel.append(box, hippo.PACK_FIXED)

		[x, y] = grid.point(1, 0)
		bottom_panel.move(box, x, y)

		right_panel = self._create_panel(grid, 15, 1, 1, 10)

		box = FriendsBox(self._shell, self._menu_shell)
		right_panel.append(box)

		left_panel = self._create_panel(grid, 0, 1, 1, 10)

	def _create_panel(self, grid, x, y, width, height):
		panel = PanelWindow()

		panel.connect('enter-notify-event', self._enter_notify_cb)
		panel.connect('leave-notify-event', self._leave_notify_cb)

		[x, y, width, height] = grid.rectangle(x, y, width, height)

		panel.move(x, y)
		panel.resize(width, height)

		self._windows.append(panel)

		return panel.get_root()

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
