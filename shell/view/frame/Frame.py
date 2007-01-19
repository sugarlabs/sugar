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

import logging
import gtk
import gobject
import hippo
import wnck

from view.frame.ActivitiesBox import ActivitiesBox
from view.frame.ZoomBox import ZoomBox
from view.frame.overlaybox import OverlayBox
from view.frame.FriendsBox import FriendsBox
from view.frame.PanelWindow import PanelWindow
from view.frame.clipboardpanelwindow import ClipboardPanelWindow
from view.frame.notificationtray import NotificationTray
from model.ShellModel import ShellModel
from sugar.graphics.timeline import Timeline
from sugar.graphics.grid import Grid
from sugar.graphics.menushell import MenuShell

class EventFrame(gobject.GObject):
    __gsignals__ = {
        'enter-edge':    (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE, ([])),
        'enter-corner':  (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE, ([])),
        'leave':         (gobject.SIGNAL_RUN_FIRST,
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

        invisible = self._create_invisible(0, 0, gtk.gdk.screen_width(), 6)
        self._windows.append(invisible)

        invisible = self._create_invisible(0, 0, 6, gtk.gdk.screen_height())
        self._windows.append(invisible)

        invisible = self._create_invisible(gtk.gdk.screen_width() - 6, 0,
                                           gtk.gdk.screen_width(),
                                           gtk.gdk.screen_height())
        self._windows.append(invisible)

        invisible = self._create_invisible(0, gtk.gdk.screen_height() - 6,
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
        
        invisible.drag_dest_set(0, [], 0)
        invisible.connect('drag_motion', self._drag_motion_cb)
        invisible.connect('drag_leave', self._drag_leave_cb)

        invisible.realize()
        invisible.window.set_events(gtk.gdk.POINTER_MOTION_MASK |
                                    gtk.gdk.ENTER_NOTIFY_MASK |
                                    gtk.gdk.LEAVE_NOTIFY_MASK)
        invisible.window.move_resize(x, y, width, height)

        return invisible

    def _enter_notify_cb(self, widget, event):
        self._notify_enter(event.x, event.y)
        logging.debug('EventFrame._enter_notify_cb ' + str(self._hover))

    def _motion_notify_cb(self, widget, event):
        self._notify_enter(event.x, event.y)
        logging.debug('EventFrame._motion_notify_cb ' + str(self._hover))
        
    def _drag_motion_cb(self, widget, drag_context, x, y, timestamp):
        drag_context.drag_status(0, timestamp);
        self._notify_enter(x, y)
        logging.debug('EventFrame._drag_motion_cb ' + str(self._hover))
        return True

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
        self._notify_leave()
        logging.debug('EventFrame._leave_notify_cb ' + str(self._hover))
        
    def _drag_leave_cb(self, widget, drag_context, timestamp):
        self._notify_leave()
        logging.debug('EventFrame._drag_leave_cb ' + str(self._hover))
        return True
        
    def _notify_leave(self):
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
        self._hover_frame = False
        self._shell = shell
        self._mode = Frame.INACTIVE

        self._timeline = Timeline(self)
        self._timeline.add_tag('slide_in', 18, 24)
        self._timeline.add_tag('before_slide_out', 48, 48)
        self._timeline.add_tag('slide_out', 49, 54)

        self._event_frame = EventFrame()
        self._event_frame.connect('enter-edge', self._enter_edge_cb)
        self._event_frame.connect('enter-corner', self._enter_corner_cb)
        self._event_frame.connect('leave', self._event_frame_leave_cb)
        self._event_frame.show()

        grid = Grid()

        # Top panel
        panel = self._create_panel(grid, 0, 0, 16, 1)
        menu_shell = panel.get_menu_shell()
        root = panel.get_root()

        menu_shell.set_position(MenuShell.BOTTOM)

        box = ZoomBox(self._shell, menu_shell)

        [x, y] = grid.point(1, 0)
        root.append(box, hippo.PACK_FIXED)
        root.set_position(box, x, y)

        tray = NotificationTray()
        tray_box = hippo.CanvasBox(box_width=grid.dimension(1),
                                   box_height=grid.dimension(1),
                                   xalign=hippo.ALIGNMENT_END)

        tray_widget = hippo.CanvasWidget()
        tray_widget.props.widget = tray
        tray_box.append(tray_widget, gtk.EXPAND)

        [x, y] = grid.point(13, 0)
        root.append(tray_box, hippo.PACK_FIXED)
        root.set_position(tray_box, x, y)

        box = OverlayBox(self._shell)

        [x, y] = grid.point(14, 0)
        root.append(box, hippo.PACK_FIXED)
        root.set_position(box, x, y)

        # Bottom panel
        panel = self._create_panel(grid, 0, 11, 16, 1)
        menu_shell = panel.get_menu_shell()
        root = panel.get_root()

        menu_shell.set_position(MenuShell.TOP)

        box = ActivitiesBox(self._shell)
        root.append(box, hippo.PACK_FIXED)

        [x, y] = grid.point(1, 0)
        root.set_position(box, x, y)

        # Right panel
        panel = self._create_panel(grid, 15, 1, 1, 10)
        menu_shell = panel.get_menu_shell()
        root = panel.get_root()

        menu_shell.set_position(MenuShell.LEFT)

        box = FriendsBox(self._shell, menu_shell)
        root.append(box)

        # Left panel
        panel = self._create_clipboard_panel(grid, 0, 1, 1, 10)

        shell.get_model().connect('notify::state',
                                  self._shell_state_changed_cb)

    def _shell_state_changed_cb(self, model, pspec):
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            self._timeline.goto('slide_out', True)
        
    def _create_clipboard_panel(self, grid, x, y, width, height):
        [x, y, width, height] = grid.rectangle(x, y, width, height)
        panel = ClipboardPanelWindow(self, x, y, width, height)

        self._connect_to_panel(panel)
        panel.connect('drag-motion', self._drag_motion_cb)
        panel.connect('drag-leave', self._drag_leave_cb)

        self._windows.append(panel)

        return panel

    def _create_panel(self, grid, x, y, width, height):
        [x, y, width, height] = grid.rectangle(x, y, width, height)
        panel = PanelWindow(x, y, width, height)
        self._connect_to_panel(panel)
        self._windows.append(panel)

        return panel

    def _connect_to_panel(self, panel):
        panel.connect('enter-notify-event', self._enter_notify_cb)
        panel.connect('leave-notify-event', self._leave_notify_cb)

        menu_shell = panel.get_menu_shell()
        menu_shell.connect('activated',
                           self._menu_shell_activated_cb)
        menu_shell.connect('deactivated',
                           self._menu_shell_deactivated_cb)

    def _menu_shell_activated_cb(self, menu_shell):
        self._timeline.goto('slide_in', True)

    def _menu_shell_deactivated_cb(self, menu_shell):
        if self._mode != Frame.STICKY and not self._hover_frame:
            self._timeline.play('before_slide_out', 'slide_out')

    def _enter_notify_cb(self, window, event):
        self._enter_notify()
        logging.debug('Frame._enter_notify_cb ' + str(self._mode))
        
    def _drag_motion_cb(self, window, context, x, y, time):
        self._enter_notify()
        logging.debug('Frame._drag_motion_cb ' + str(self._mode))
        return True
        
    def _drag_leave_cb(self, window, drag_context, timestamp):
        self._leave_notify(window)
        logging.debug('Frame._drag_leave_cb ' + str(self._mode))
            
    def _leave_notify_cb(self, window, event):
        # FIXME for some reason every click cause also a leave-notify
        if event.state == gtk.gdk.BUTTON1_MASK:
            return

        self._leave_notify(window)
        logging.debug('Frame._leave_notify_cb ' + str(self._mode))

    def _enter_notify(self):
        self._hover_frame = True
        self._timeline.goto('slide_in', True) 
               
    def _leave_notify(self, panel):
        self._hover_frame = False
        if not panel.get_menu_shell().is_active() and \
           (self._mode == Frame.HIDE_ON_LEAVE or \
            self._mode == Frame.AUTOMATIC):
            self._timeline.play('before_slide_out', 'slide_out')

    def _enter_edge_cb(self, event_frame):
        self._mode = Frame.HIDE_ON_LEAVE
        self._timeline.play(None, 'slide_in')
        logging.debug('Frame._enter_edge_cb ' + str(self._mode))
        
    def _enter_corner_cb(self, event_frame):
        self._mode = Frame.HIDE_ON_LEAVE
        self._timeline.play('slide_in', 'slide_in')
        logging.debug('Frame._enter_corner_cb ' + str(self._mode))
        
    def _event_frame_leave_cb(self, event_frame):
        if self._mode != Frame.STICKY:
            self._timeline.goto('slide_out', True)
        logging.debug('Frame._event_frame_leave_cb ' + str(self._mode))
        
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
