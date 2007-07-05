# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com)
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging

import gtk
import gobject
import time
import hippo

from sugar.graphics import animator
from sugar.graphics import units
from sugar import _sugarext

_BOTTOM_LEFT  = 0
_BOTTOM_RIGHT = 1
_LEFT_BOTTOM  = 2
_LEFT_TOP     = 3
_RIGHT_BOTTOM = 4
_RIGHT_TOP    = 5
_TOP_LEFT     = 6
_TOP_RIGHT    = 7

class Palette(gobject.GObject):
    AUTOMATIC = 0
    BOTTOM    = 1
    LEFT      = 2
    RIGHT     = 3
    TOP       = 4

    __gtype_name__ = 'SugarPalette'

    __gproperties__ = {
        'invoker'    : (object, None, None,
                        gobject.PARAM_READWRITE),
        'position'   : (gobject.TYPE_INT, None, None, 0, 5,
                        0, gobject.PARAM_READWRITE)
    }

    def __init__(self, label, accel_path=None):
        gobject.GObject.__init__(self)

        self._position = self.AUTOMATIC
        self._palette_popup_sid = None

        self._popup_anim = animator.Animator(0.3, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._secondary_anim = animator.Animator(1.3, 10)
        self._secondary_anim.add(_SecondaryAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        self._menu = _sugarext.Menu()

        self._primary = _PrimaryMenuItem(label, accel_path)
        self._menu.append(self._primary)
        self._primary.show()

        self._separator = gtk.SeparatorMenuItem()
        self._menu.append(self._separator)

        self._content = _ContentMenuItem()
        self._menu.append(self._content)

        self._button_bar = _ButtonBarMenuItem()
        self._menu.append(self._button_bar)

        self._menu.connect('enter-notify-event',
                           self._enter_notify_event_cb)
        self._menu.connect('leave-notify-event',
                           self._leave_notify_event_cb)
        self._menu.connect('button-press-event',
                           self._button_press_event_cb)

    def set_primary_text(self, label, accel_path=None):
        self._primary.set_label(label, accel_path)

    def append_menu_item(self, item):
        self._separator.show()
        self._menu.insert(item, len(self._menu.get_children()) - 2)

    def insert_menu_item(self, item, index=-1):
        self._separator.show()
        if index < 0:
            self._menu.insert(item, len(self._menu.get_children()) - 2)
        else:
            self._menu.insert(item, index + 2)

    def remove_menu_item(self, index):
        if index > len(self._menu.get_children()) - 4:
            raise ValueError('index %i out of range' % index)
        self._menu.remove(self._menu.get_children()[index + 2])
        if len(self._menu.get_children()) == 0:
            self._separator.hide()

    def menu_item_count(self):
        return len(self._menu.get_children()) - 4
        
    def set_content(self, widget):
        self._content.set_widget(widget)
        self._content.show()

    def append_button(self, button):
        self._button_bar.append_button(button)
        self._button_bar.show()
        
    def do_set_property(self, pspec, value):
        if pspec.name == 'invoker':
            self._invoker = value
            self._invoker.add_listener(self)
        elif pspec.name == 'position':
            self._position = value
        else:
            raise AssertionError

    def _get_position(self, alignment):
        # Invoker: x, y, width and height
        inv_rect = self._invoker.get_rect()
        palette_width, palette_height = self._menu.size_request()

        if alignment == _BOTTOM_LEFT:
            x = inv_rect.x
            y = inv_rect.y + inv_rect.height
        elif alignment == _BOTTOM_RIGHT:
            x = (inv_rect.x + inv_rect.width) - palette_width
            y = inv_rect.y + inv_rect.height
        elif alignment == _LEFT_BOTTOM:
            x = inv_rect.x - palette_width
            y = inv_rect.y
        elif alignment == _LEFT_TOP:
            x = inv_rect.x - palette_width
            y = (inv_rect.y + inv_rect.height) - palette_height
        elif alignment == _RIGHT_BOTTOM:
            x = inv_rect.x + inv_rect.width
            y = inv_rect.y
        elif alignment == _RIGHT_TOP:
            x = inv_rect.x + inv_rect.width
            y = (inv_rect.y + inv_rect.height) - palette_height
        elif alignment == _TOP_LEFT:
            x = inv_rect.x
            y = inv_rect.y - palette_height
        elif alignment == _TOP_RIGHT:
            x = (inv_rect.x + inv_rect.width) - palette_width
            y = inv_rect.y - palette_height

        return x, y

    def _in_screen(self, x, y):
        [width, height] = self._menu.size_request()
        screen_width = gtk.gdk.screen_width() - units.grid_to_pixels(1)
        screen_height = gtk.gdk.screen_height() - units.grid_to_pixels(1)

        return x + width <= screen_width and \
               y + height <= screen_height and \
               x >= units.grid_to_pixels(1) and y >= units.grid_to_pixels(1)

    def _get_automatic_position(self):
        alignments = [ _BOTTOM_LEFT,  _BOTTOM_RIGHT,
                       _LEFT_BOTTOM,  _LEFT_TOP,
                       _RIGHT_BOTTOM, _RIGHT_TOP,
                       _TOP_LEFT,     _TOP_RIGHT ]

        for alignment in alignments:
            x, y = self._get_position(alignment)
            if self._in_screen(x, y):
                return x, y

    def _show(self):
        x = y = 0

        if self._position == self.AUTOMATIC:
            x, y = self._get_automatic_position()
        elif self._position == self.BOTTOM:
            x, y = self._get_position(_BOTTOM_LEFT)
            if not self._in_screen(x, y):
                x, y = self._get_position(_BOTTOM_RIGHT)
        elif self._position == self.LEFT:
            x, y = self._get_position(_LEFT_BOTTOM)
            if not self._in_screen(x, y):
                x, y = self._get_position(_LEFT_TOP)
        elif self._position == self.RIGHT:
            x, y = self._get_position(_RIGHT_BOTTOM)
            if not self._in_screen(x, y):
                x, y = self._get_position(_RIGHT_TOP)
        elif self._position == self.TOP:
            x, y = self._get_position(_TOP_LEFT)
            if not self._in_screen(x, y):
                x, y = self._get_position(_TOP_RIGHT)

        self._palette_popup_sid = _palette_observer.connect('popup',
                    self._palette_observer_popup_cb)
        self._menu.popup(x, y)
        _palette_observer.emit('popup', self)

    def _hide(self):
        if not self._palette_popup_sid is None:
            _palette_observer.disconnect(self._palette_popup_sid)
            self._palette_popup_sid = None
        self._menu.popdown()

    def popup(self):
        self._popdown_anim.stop()
        self._popup_anim.start()
        self._secondary_anim.start()

    def popdown(self):
        self._secondary_anim.stop()
        self._popup_anim.stop()
        self._popdown_anim.start()

    def invoker_mouse_enter(self):
        self.popup()

    def invoker_mouse_leave(self):
        self.popdown()

    def _enter_notify_event_cb(self, widget, event):
        if event.detail == gtk.gdk.NOTIFY_NONLINEAR:
            self._popdown_anim.stop()

    def _leave_notify_event_cb(self, widget, event):
        if event.detail == gtk.gdk.NOTIFY_NONLINEAR:
            self.popdown()

    def _button_press_event_cb(self, widget, event):
        pass

    def _palette_observer_popup_cb(self, observer, palette):
        if self != palette:
            self._hide()

class _PrimaryMenuItem(gtk.MenuItem):
    def __init__(self, label, accel_path):
        gtk.MenuItem.__init__(self)
        self._set_label(label, accel_path)

    def set_label(self, label, accel_path):
        self.remove(self._label)
        self._set_label(label, accel_path)

    def _set_label(self, label, accel_path):
        self._label = gtk.AccelLabel(label)
        self._label.set_accel_widget(self)

        if accel_path:
            self.set_accel_path(accel_path)
            self._label.set_alignment(0.0, 0.5)

        self.add(self._label)
        self._label.show()
    
class _ContentMenuItem(gtk.MenuItem):
    def __init__(self):
        gtk.MenuItem.__init__(self)

    def set_widget(self, widget):
        if self.child:
            self.remove(self.child)
        self.add(widget)

    def is_empty(self):
        return self.child is None

class _ButtonBarMenuItem(gtk.MenuItem):
    def __init__(self):
        gtk.MenuItem.__init__(self)

        self._hbar = gtk.HButtonBox()
        self.add(self._hbar)
        self._hbar.show()

    def append_button(self, button):
        self._hbar.pack_start(button)

    def is_empty(self):
        return len(self._hbar.get_children()) == 0

class _PopupAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._primary.show()
            for menu_item in self._palette._menu.get_children()[1:]:
                menu_item.hide()
            self._palette._show()

class _SecondaryAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            middle_menu_items = self._palette._menu.get_children()
            middle_menu_items = middle_menu_items[2:len(middle_menu_items) - 2]
            if middle_menu_items or \
                    not self._palette._content.is_empty() or \
                    not self._palette._button_bar.is_empty():
                self._palette._separator.show()

            for menu_item in middle_menu_items:
                menu_item.show()

            if not self._palette._content.is_empty():
                self._palette._content.show()

            if not self._palette._button_bar.is_empty():
                self._palette._button_bar.show()

            self._palette._show()

class _PopdownAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._hide()

class Invoker(object):
    def __init__(self):
        self._listeners = []

    def add_listener(self, listener):
        self._listeners.append(listener)

    def notify_mouse_enter(self):
        for listener in self._listeners:
            listener.invoker_mouse_enter()

    def notify_mouse_leave(self):
        for listener in self._listeners:
            listener.invoker_mouse_leave()

class WidgetInvoker(Invoker):
    def __init__(self, widget):
        Invoker.__init__(self)
        self._widget = widget

        widget.connect('enter-notify-event', self._enter_notify_event_cb)
        widget.connect('leave-notify-event', self._leave_notify_event_cb)

    def get_rect(self):
        win_x, win_y = self._widget.window.get_origin()
        rectangle = self._widget.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        width = rectangle.width
        height = rectangle.height

        return gtk.gdk.Rectangle(x, y, width, height)

    def _enter_notify_event_cb(self, widget, event):
        self.notify_mouse_enter()

    def _leave_notify_event_cb(self, widget, event):
        self.notify_mouse_leave()

class CanvasInvoker(Invoker):
    def __init__(self, item):
        Invoker.__init__(self)
        self._item = item

        item.connect('motion-notify-event',
                     self._motion_notify_event_cb)

    def get_rect(self):
        context = self._item.get_context()
        if context:
            x, y = context.translate_to_screen(self._item)

        width, height = self._item.get_allocation()

        return gtk.gdk.Rectangle(x, y, width, height)

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.notify_mouse_enter()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.notify_mouse_leave()

        return False

class _PaletteObserver(gobject.GObject):
    __gtype_name__ = 'SugarPaletteObserver'

    __gsignals__ = {
        'popup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

_palette_observer = _PaletteObserver()
