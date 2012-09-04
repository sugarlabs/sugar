# Copyright (C) 2007, Red Hat, Inc.
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

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Wnck
from gi.repository import GConf


_MAX_DELAY = 1000


class EventArea(GObject.GObject):
    __gsignals__ = {
        'enter': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'leave': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self._windows = []
        self._hover = False
        self._sids = {}
        client = GConf.Client.get_default()
        self._edge_delay = client.get_int('/desktop/sugar/frame/edge_delay')
        self._corner_delay = client.get_int('/desktop/sugar/frame'
                                            '/corner_delay')

        right = Gdk.Screen.width() - 1
        bottom = Gdk.Screen.height() - 1
        width = Gdk.Screen.width() - 2
        height = Gdk.Screen.height() - 2

        if self._edge_delay != _MAX_DELAY:
            invisible = self._create_invisible(1, 0, width, 1,
                                               self._edge_delay)
            self._windows.append(invisible)

            invisible = self._create_invisible(1, bottom, width, 1,
                                               self._edge_delay)
            self._windows.append(invisible)

            invisible = self._create_invisible(0, 1, 1, height,
                                               self._edge_delay)
            self._windows.append(invisible)

            invisible = self._create_invisible(right, 1, 1, height,
                                               self._edge_delay)
            self._windows.append(invisible)

        if self._corner_delay != _MAX_DELAY:
            invisible = self._create_invisible(0, 0, 1, 1,
                                               self._corner_delay)
            self._windows.append(invisible)

            invisible = self._create_invisible(right, 0, 1, 1,
                                               self._corner_delay)
            self._windows.append(invisible)

            invisible = self._create_invisible(0, bottom, 1, 1,
                                               self._corner_delay)
            self._windows.append(invisible)

            invisible = self._create_invisible(right, bottom, 1, 1,
                                               self._corner_delay)
            self._windows.append(invisible)

        screen = Wnck.Screen.get_default()
        screen.connect('window-stacking-changed',
                       self._window_stacking_changed_cb)

    def _create_invisible(self, x, y, width, height, delay):
        invisible = Gtk.Invisible()
        if delay >= 0:
            invisible.connect('enter-notify-event', self._enter_notify_cb,
                              delay)
            invisible.connect('leave-notify-event', self._leave_notify_cb)

        invisible.drag_dest_set(0, [], 0)
        invisible.connect('drag_motion', self._drag_motion_cb)
        invisible.connect('drag_leave', self._drag_leave_cb)

        invisible.realize()
        # pylint: disable=E1101
        x11_window = invisible.get_window()
        x11_window.set_events(Gdk.EventMask.POINTER_MOTION_MASK |
                              Gdk.EventMask.ENTER_NOTIFY_MASK |
                              Gdk.EventMask.LEAVE_NOTIFY_MASK)
        x11_window.move_resize(x, y, width, height)

        return invisible

    def _notify_enter(self):
        if not self._hover:
            self._hover = True
            self.emit('enter')

    def _notify_leave(self):
        if self._hover:
            self._hover = False
            self.emit('leave')

    def _enter_notify_cb(self, widget, event, delay):
        if widget in self._sids:
            GObject.source_remove(self._sids[widget])
        self._sids[widget] = GObject.timeout_add(delay,
                                                 self.__delay_cb,
                                                 widget)

    def __delay_cb(self, widget):
        del self._sids[widget]
        self._notify_enter()
        return False

    def _leave_notify_cb(self, widget, event):
        if widget in self._sids:
            GObject.source_remove(self._sids[widget])
            del self._sids[widget]
        self._notify_leave()

    def _drag_motion_cb(self, widget, drag_context, x, y, timestamp):
        drag_context.drag_status(0, timestamp)
        self._notify_enter()
        return True

    def _drag_leave_cb(self, widget, drag_context, timestamp):
        self._notify_leave()
        return True

    def show(self):
        for window in self._windows:
            window.show()

    def hide(self):
        for window in self._windows:
            window.hide()

    def _window_stacking_changed_cb(self, screen):
        for window in self._windows:
            window.get_window().raise_()
