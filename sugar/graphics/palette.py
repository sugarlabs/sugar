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

import gtk
import gobject
import time
import hippo

from sugar.graphics import animator

ALIGNMENT_AUTOMATIC     = 0
ALIGNMENT_BOTTOM_LEFT   = 1
ALIGNMENT_BOTTOM_RIGHT  = 2
ALIGNMENT_LEFT_BOTTOM   = 3
ALIGNMENT_LEFT_TOP      = 4
ALIGNMENT_RIGHT_BOTTOM  = 5
ALIGNMENT_RIGHT_TOP     = 6
ALIGNMENT_TOP_LEFT      = 7
ALIGNMENT_TOP_RIGHT     = 8

class Palette(gtk.Window):
    __gtype_name__ = 'SugarPalette'

    __gproperties__ = {
        'invoker'    : (object, None, None,
                        gobject.PARAM_READWRITE),
        'alignment'  : (gobject.TYPE_INT, None, None, 0, 8,
                        ALIGNMENT_AUTOMATIC,
                        gobject.PARAM_READWRITE)
    }

    _PADDING    = 1
    _WIN_BORDER = 5

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, type=gtk.WINDOW_POPUP, **kwargs)
        gtk.Window.__init__(self)

        self._alignment = ALIGNMENT_AUTOMATIC

        self._popup_anim = animator.Animator(0.6, 10)
        self._popup_anim.add(_PopupAnimation(self))
        self._popup_anim.start()

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))
        self._popdown_anim.start()

        self._palette_label = gtk.Label()
        self._palette_label.show()

        vbox = gtk.VBox(False, 0)
        vbox.pack_start(self._palette_label, True, True, self._PADDING)

        self._separator = gtk.HSeparator()

        self._menu_bar = gtk.MenuBar()
        self._menu_bar.set_pack_direction(gtk.PACK_DIRECTION_TTB)

        self._content = gtk.HBox()
        self._button_bar = gtk.HButtonBox()
    
        # Set main container
        vbox.pack_start(self._separator, True, True, self._PADDING)
        vbox.pack_start(self._menu_bar, True, True, self._PADDING)
        vbox.pack_start(self._content, True, True, self._PADDING)
        vbox.pack_start(self._button_bar, True, True, self._PADDING)

        vbox.show()
        self.add(vbox)

        # Widget events
        self.connect('enter-notify-event', self._enter_notify_event_cb)
        self.connect('leave-notify-event', self._leave_notify_event_cb)
        self.connect('button-press-event', self._button_press_event_cb)

        self.set_border_width(self._WIN_BORDER)
        
    def do_set_property(self, pspec, value):
        if pspec.name == 'invoker':
            self._invoker = value
            self._invoker.add_listener(self)
        elif pspec.name == 'alignment':
            self._alignment = value
        else:
            raise AssertionError

    def place(self):
        # Automatic Alignment
        if self._alignment == ALIGNMENT_AUTOMATIC:
            # Trying Different types of ALIGNMENTS, 
            # and return the choosen one
            if self._try_position(ALIGNMENT_BOTTOM_LEFT):
                return ALIGNMENT_BOTTOM_LEFT
            elif self._try_position(ALIGNMENT_BOTTOM_RIGHT):
                return ALIGNMENT_BOTTOM_RIGHT
            elif self._try_position(ALIGNMENT_LEFT_BOTTOM):
                return ALIGNMENT_LEFT_BOTTOM
            elif self._try_position(ALIGNMENT_LEFT_TOP):
                return ALIGNMENT_LEFT_TOP
            elif self._try_position(ALIGNMENT_RIGHT_BOTTOM):
                return ALIGNMENT_RIGHT_BOTTOM
            elif self._try_position(ALIGNMENT_RIGHT_TOP):
                return ALIGNMENT_RIGHT_TOP
            elif self._try_position(ALIGNMENT_TOP_LEFT):
                return ALIGNMENT_TOP_LEFT
            elif self._try_position(ALIGNMENT_TOP_RIGHT):
                return ALIGNMENT_TOP_RIGHT
        else:
            # Manual Alignment
            move_x, move_y = self._calc_position(self._alignment)
            self.move(move_x, move_y)

    def _try_position(self, alignment):
        screen_width = gtk.gdk.screen_width()
        screen_height = gtk.gdk.screen_height()
        x, y = self._calc_position(alignment)
        self._width, self._height = self.size_request()

        if (x + self._width > screen_width) or \
           (y + self._height > screen_height):
            return False
        else:
            self.move(x, y)
            self.show()
            return True

    def _calc_position(self, alignment):
        # Invoker: x, y, width and height
        inv_rect = self._invoker.get_rect()
        palette_rectangle = self.get_allocation()

        if alignment == ALIGNMENT_BOTTOM_LEFT:
            move_x = inv_rect.x
            move_y = inv_rect.y + inv_rect.height

        elif alignment == ALIGNMENT_BOTTOM_RIGHT:
            move_x = (inv_rect.x + inv_rect.width) - self._width
            move_y = inv_rect.y + inv_rect.height

        elif alignment == ALIGNMENT_LEFT_BOTTOM:
            move_x = inv_rect.x - self._width
            move_y = inv_rect.y

        elif alignment == ALIGNMENT_LEFT_TOP:
            move_x = inv_rect.x - self._width
            move_y = (inv_rect.y + inv_rect.height) - palette_rectangle.height

        elif alignment == ALIGNMENT_RIGHT_BOTTOM:
            move_x = inv_rect.x + inv_rect.width
            move_y = inv_rect.y

        elif alignment == ALIGNMENT_RIGHT_TOP:
            move_x = inv_rect.x + inv_rect.width
            move_y = (inv_rect.y + inv_rect.height) - palette_rectangle.height

        elif alignment == ALIGNMENT_TOP_LEFT:
            move_x = inv_rect.x
            move_y = inv_rect.y - palette_rectangle.height

        elif alignment == ALIGNMENT_TOP_RIGHT:
            move_x = (inv_rect.x + inv_rect.width) - self._width
            move_y = inv_rect.y - palette_rectangle.height

        return move_x, move_y

    def set_primary_state(self, label, accel_path=None):
        if accel_path != None:
            item = gtk.MenuItem(label)
            item.set_accel_path(accel_path)
            self.append_menu_item(item)
            self._separator.hide()
        else:
            self._palette_label.set_text(label)

    def append_menu_item(self, item):
        self._separator.show()
        self._menu_bar.show()
        self._menu_bar.append(item)
        item.show()

    def set_content(self, widget):
        self._separator.show()
        self._content.pack_start(widget, True, True, self._PADDING)
        widget.show()

    def append_button(self, button):
        button.connect('released', self._close_palette_cb)
        self._button_bar.pack_start(button, True, True, self._PADDING)
        button.show()

    def popup(self):
        self._popdown_anim.stop()
        self._popup_anim.start()

    def popdown(self):
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

class _PopupAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette.place()

class _PopdownAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette.hide()

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
        x, y = context.translate_to_screen(self._item)
        width, height = self._item.get_allocation()

        return gtk.gdk.Rectangle(x, y, width, height)

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.notify_mouse_enter()
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.notify_mouse_leave()

        return False
