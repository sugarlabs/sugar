import logging

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, GLib, Gdk

HAS_LAYER_SHELL = False

from sugar4.graphics import style

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
        super().__init__()
        

        self._hover = False
        self._is_active = False
        self._sids = {}

        self._boxes = {}
        self._tags = {}
        
        self._edge_delay = _MAX_DELAY
        self._corner_delay = _MAX_DELAY



        for tag in _BOXES:
            box = self._box(tag)
            self._tags[box] = tag
            self._boxes[tag] = box

        settings.connect('changed', self._settings_changed_cb)
        self._settings_changed_cb(settings, None)

    def _box(self, tag):
        window = Gtk.Box()
        window.add_css_class('transparent-window')
        
        provider = Gtk.CssProvider()
        provider.load_from_string('.transparent-window, .transparent-window:hover { background-color: rgba(0, 0, 0, 0.01); }')
        window.get_style_context().add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        
        if tag == 'nw':
            window.set_valign(Gtk.Align.START)
            window.set_halign(Gtk.Align.START)
        elif tag == 'ne':
            window.set_valign(Gtk.Align.START)
            window.set_halign(Gtk.Align.END)
        elif tag == 'se':
            window.set_valign(Gtk.Align.END)
            window.set_halign(Gtk.Align.END)
        elif tag == 'sw':
            window.set_valign(Gtk.Align.END)
            window.set_halign(Gtk.Align.START)
        elif tag == 'n':
            window.set_valign(Gtk.Align.START)
            window.set_halign(Gtk.Align.FILL)
        elif tag == 's':
            window.set_valign(Gtk.Align.END)
            window.set_halign(Gtk.Align.FILL)
        elif tag == 'e':
            window.set_valign(Gtk.Align.FILL)
            window.set_halign(Gtk.Align.END)
        elif tag == 'w':
            window.set_valign(Gtk.Align.FILL)
            window.set_halign(Gtk.Align.START)


        controller = Gtk.EventControllerMotion()
        controller.connect('enter', self._enter_notify_cb, window)
        controller.connect('leave', self._leave_notify_cb, window)
        window.add_controller(controller)

        # Drop support
        drop_target = Gtk.DropTargetAsync.new(None, Gdk.DragAction.COPY)
        drop_target.connect('accept', self._drag_accept_cb, window)
        drop_target.connect('drag-enter', self._drag_motion_cb, window)
        drop_target.connect('drag-leave', self._drag_leave_cb, window)
        window.add_controller(drop_target)
        
        return window

    def _settings_changed_cb(self, settings, key):
        self._edge_delay = min(settings.get_int('edge-delay'), _MAX_DELAY)
        self._corner_delay = min(settings.get_int('corner-delay'), _MAX_DELAY)
        ts = min(settings.get_int('trigger-size'), style.GRID_CELL_SIZE)

        if self._edge_delay == _MAX_DELAY:
            self._hide(_EDGES)
        else:
            self._move('n', ts)
            self._move('e', ts)
            self._move('s', ts)
            self._move('w', ts)

        if self._corner_delay == _MAX_DELAY:
            self._hide(_CORNERS)
        else:
            self._move('nw', ts)
            self._move('ne', ts)
            self._move('se', ts)
            self._move('sw', ts)

    def _hide(self, tags):
        for tag in tags:
            self._boxes[tag].set_visible(False)

    def _move(self, tag, ts):
        window = self._boxes[tag]
        if tag in ['n', 's']:
            window.set_size_request(-1, ts)
            window.set_margin_start(ts)
            window.set_margin_end(ts)
        elif tag in ['e', 'w']:
            window.set_size_request(ts, -1)
            window.set_margin_top(ts)
            window.set_margin_bottom(ts)
        else:
            window.set_size_request(ts, ts)
            
        if self._is_active:
            window.set_visible(True)

    def _notify_enter(self):
        if not self._hover:
            self._hover = True
            self.emit('enter')

    def _notify_leave(self):
        if self._hover:
            self._hover = False
            self.emit('leave')

    def _enter_notify_cb(self, controller, x, y, window):
        if window in self._sids:
            GLib.source_remove(self._sids[window])
            del self._sids[window]

        delay = None
        if self._tags[window] in _CORNERS:
            delay = self._corner_delay
        if self._tags[window] in _EDGES:
            delay = self._edge_delay

        if delay is not None:
            self._sids[window] = GLib.timeout_add(delay, self.__delay_cb, window)

    def __delay_cb(self, window):
        del self._sids[window]
        self._notify_enter()
        return False

    def _leave_notify_cb(self, controller, window):
        if window in self._sids:
            GLib.source_remove(self._sids[window])
            del self._sids[window]
        self._notify_leave()

    def _drag_accept_cb(self, drop_target, drop, window):
        return True

    def _drag_motion_cb(self, drop_target, drop, x, y, window):
        self._notify_enter()
        return Gdk.DragAction.COPY

    def _drag_leave_cb(self, drop_target, drop, window):
        self._notify_leave()

    def show(self):
        self._is_active = True
        if not HAS_LAYER_SHELL:
            return
        for tag in _BOXES:
            delay = self._corner_delay if tag in _CORNERS else self._edge_delay
            if delay != _MAX_DELAY:
                self._boxes[tag].set_visible(True)

    def hide(self):
        self._is_active = False
        if not HAS_LAYER_SHELL:
            return
        for box in list(self._boxes.values()):
            box.set_visible(False)

    def set_visible(self, visible):
        if visible:
            self.show()
        else:
            self.hide()
