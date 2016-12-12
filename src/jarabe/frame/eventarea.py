# Copyright (C) 2007, Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GObject
from gi.repository import Wnck

from sugar3.graphics import style


_MAX_DELAY = 1000

_CORNERS = ['nw', 'ne', 'se', 'sw']
_EDGES = ['n', 'e', 's', 'w']
_BOXES = _CORNERS + _EDGES


class EventArea(GObject.GObject):
    __gsignals__ = {
        'enter': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'leave': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self, settings):
        GObject.GObject.__init__(self)

        self._hover = False
        self._sids = {}

        self._boxes = {}
        self._tags = {}
        for tag in _BOXES:
            box = self._box(tag)
            self._tags[box] = tag
            self._boxes[tag] = box

        settings.connect('changed', self._settings_changed_cb)
        self._settings_changed_cb(settings, None)

        screen = Wnck.Screen.get_default()
        screen.connect('window-stacking-changed',
                       self._window_stacking_changed_cb)

    def _box(self, tag):
        box = Gtk.Invisible()
        box.connect('enter-notify-event', self._enter_notify_cb)
        box.connect('leave-notify-event', self._leave_notify_cb)
        box.drag_dest_set(0, [], 0)
        box.connect('drag_motion', self._drag_motion_cb)
        box.connect('drag_leave', self._drag_leave_cb)
        box.realize()
        return box

    def _settings_changed_cb(self, settings, key):
        self._edge_delay = min(settings.get_int('edge-delay'), _MAX_DELAY)
        self._corner_delay = min(settings.get_int('corner-delay'), _MAX_DELAY)
        ts = min(settings.get_int('trigger-size'), style.GRID_CELL_SIZE)
        sw = Gdk.Screen.width()
        sh = Gdk.Screen.height()

        if self._edge_delay == _MAX_DELAY:
            self._hide(_EDGES)
        else:
            self._move('n', ts, -1, sw - ts * 2, ts + 1)
            self._move('e', -1, ts, ts + 1, sh - ts * 2)
            self._move('s', ts, sh - ts, sw - ts * 2, ts + 1)
            self._move('w', sw - ts, ts, ts + 1, sh - ts * 2)

        if self._corner_delay == _MAX_DELAY:
            self._hide(_CORNERS)
        else:
            self._move('nw', -1, -1, ts + 1, ts + 1)
            self._move('ne', sw - ts, -1, ts + 1, ts + 1)
            self._move('se', sw - ts, sh - ts, ts + 1, ts + 1)
            self._move('sw', -1, sh - ts, ts + 1, ts + 1)

    def _hide(self, tags):
        for tag in tags:
            self._move(tag, -20, -20, 1, 1)

    def _move(self, tag, x, y, width, height):
        window = self._boxes[tag].get_window()
        window.set_events(Gdk.EventMask.POINTER_MOTION_MASK |
                          Gdk.EventMask.ENTER_NOTIFY_MASK |
                          Gdk.EventMask.LEAVE_NOTIFY_MASK)
        window.move_resize(x, y, width, height)

    def _notify_enter(self):
        if not self._hover:
            self._hover = True
            self.emit('enter')

    def _notify_leave(self):
        if self._hover:
            self._hover = False
            self.emit('leave')

    def _enter_notify_cb(self, widget, event):
        if self._sids:
            GObject.source_remove(widget.sid)
            del self._sids[widget]

        delay = None
        if self._tags[widget] in _CORNERS:
            delay = self._corner_delay
        if self._tags[widget] in _EDGES:
            delay = self._edge_delay

        if delay is not None:
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
        Gdk.drag_status(drag_context, 0, timestamp)
        self._notify_enter()
        return True

    def _drag_leave_cb(self, widget, drag_context, timestamp):
        self._notify_leave()
        return True

    def show(self):
        for box in self._boxes.itervalues():
            box.show()

    def hide(self):
        for box in self._boxes.itervalues():
            box.hide()

    def _window_stacking_changed_cb(self, screen):
        for box in self._boxes.itervalues():
            box.get_window().raise_()
