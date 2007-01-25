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
import wnck

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
