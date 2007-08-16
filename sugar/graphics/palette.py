# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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

from sugar.graphics import palettegroup
from sugar.graphics import animator
from sugar.graphics import style
from sugar import _sugaruiext

_BOTTOM_LEFT  = 0
_BOTTOM_RIGHT = 1
_LEFT_BOTTOM  = 2
_LEFT_TOP     = 3
_RIGHT_BOTTOM = 4
_RIGHT_TOP    = 5
_TOP_LEFT     = 6
_TOP_RIGHT    = 7


# Helper function to find the gap position and size of widget a
def _calculate_gap(a, b):
    # Test for each side if the palette and invoker are
    # adjacent to each other.
    gap = True

    if a.y + a.height == b.y:
        gap_side = gtk.POS_BOTTOM
    elif a.x + a.width == b.x:
        gap_side = gtk.POS_RIGHT
    elif a.x == b.x + b.width:
        gap_side = gtk.POS_LEFT
    elif a.y == b.y + b.height:
        gap_side = gtk.POS_TOP
    else:
        gap = False
    
    if gap:
        if gap_side == gtk.POS_BOTTOM or gap_side == gtk.POS_TOP:
            gap_start = min(a.width, max(0, b.x - a.x))
            gap_size = max(0, min(a.width,
                                  (b.x + b.width) - a.x) - gap_start)
        elif gap_side == gtk.POS_RIGHT or gap_side == gtk.POS_LEFT:
            gap_start = min(a.height, max(0, b.y - a.y))
            gap_size = max(0, min(a.height,
                                  (b.y + b.height) - a.y) - gap_start)

    if gap and gap_size > 0:
        return (gap_side, gap_start, gap_size)
    else:
        return False

class Palette(gtk.Window):
    DEFAULT   = 0
    AT_CURSOR = 1
    AROUND    = 2
    BOTTOM    = 3
    LEFT      = 4
    RIGHT     = 5
    TOP       = 6

    _PRIMARY = 0
    _SECONDARY = 1

    __gtype_name__ = 'SugarPalette'

    __gproperties__ = {
        'invoker'    : (object, None, None,
                        gobject.PARAM_READWRITE),
        'position'   : (gobject.TYPE_INT, None, None, 0, 6,
                        0, gobject.PARAM_READWRITE)
    }

    __gsignals__ = {
        'popup' :   (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([])),
        'popdown' : (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([]))
    }

    def __init__(self, label, accel_path=None):
        gtk.Window.__init__(self)

        self.set_decorated(False)
        self.set_resizable(False)
        self.connect('realize', self._realize_cb)

        self._full_request = [0, 0]
        self._cursor_x = 0
        self._cursor_y = 0
        self._state = self._PRIMARY
        self._invoker = None
        self._group_id = None
        self._up = False
        self._position = self.DEFAULT
        self._palette_popup_sid = None

        self._popup_anim = animator.Animator(0.3, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._secondary_anim = animator.Animator(1.0, 10)
        self._secondary_anim.add(_SecondaryAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        vbox = gtk.VBox()
        vbox.set_border_width(style.DEFAULT_PADDING)

        self._label = gtk.Label()
        vbox.pack_start(self._label, False)

        self._secondary_box = gtk.VBox()
        vbox.pack_start(self._secondary_box)

        self._separator = gtk.HSeparator()
        self._secondary_box.pack_start(self._separator)

        self._menu_box = gtk.VBox()
        self._secondary_box.pack_start(self._menu_box)
        self._menu_box.show()

        self._content = gtk.VBox()
        self._secondary_box.pack_start(self._content)
        self._content.show()

        self.action_bar = PaletteActionBar()
        self._secondary_box.pack_start(self.action_bar)
        self.action_bar.show()

        self.add(vbox)
        vbox.show()

        self.menu = _Menu(self)
        self.menu.show()

        self.connect('enter-notify-event',
                     self._enter_notify_event_cb)
        self.connect('leave-notify-event',
                     self._leave_notify_event_cb)

        self.set_primary_text(label, accel_path)

    def is_up(self):
        return self._up

    def get_rect(self):
        win_x, win_y = self.window.get_origin()
        rectangle = self.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        width = rectangle.width
        height = rectangle.height
        
        return gtk.gdk.Rectangle(x, y, width, height)

    def set_primary_text(self, label, accel_path=None):
        self._label.set_text(label)
        self._label.show()

    def set_content(self, widget):
        if len(self._content.get_children()) > 0:
            self.remove(self._content.get_children()[0])

        if widget is not None:
            self._content.add(widget)

        self._update_accept_focus()
        self._update_separator()

    def set_group_id(self, group_id):
        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            group.remove(self)
        if group_id:
            group = palettegroup.get_group(group_id)
            group.add(self)

    def do_set_property(self, pspec, value):
        if pspec.name == 'invoker':
            self._invoker = value
            self._invoker.connect('mouse-enter', self._invoker_mouse_enter_cb)
            self._invoker.connect('mouse-leave', self._invoker_mouse_leave_cb)
        elif pspec.name == 'position':
            self._position = value
        else:
            raise AssertionError

    def do_get_property(self, pspec):
        if pspec.name == 'invoker':
            return self._invoker
        elif pspec.name == 'position':
            return self._position
        else:
            raise AssertionError

    def do_size_allocate(self, allocation):
        gtk.Window.do_size_allocate(self, allocation)
        self.queue_draw()

    def do_expose_event(self, event):
        # We want to draw a border with a beautiful gap
        if self._invoker.has_rectangle_gap():
            invoker = self._invoker.get_rect()
            palette = self.get_rect()

            gap = _calculate_gap(palette, invoker)
        else:
            gap = False

        if gap:
            self.style.paint_box_gap(event.window, gtk.STATE_PRELIGHT,
                                     gtk.SHADOW_IN, event.area, self, "palette",
                                     0, 0, 
                                     self.allocation.width,
                                     self.allocation.height,
                                     gap[0], gap[1], gap[2])
        else:
            self.style.paint_box(event.window, gtk.STATE_PRELIGHT,
                                 gtk.SHADOW_IN, event.area, self, "palette",
                                 0, 0,
                                 self.allocation.width,
                                 self.allocation.height)

        # Fall trough to the container expose handler.
        # (Leaving out the window expose handler which redraws everything)
        gtk.Bin.do_expose_event(self, event)

    def _update_separator(self):
        visible = len(self.menu.get_children()) > 0 or  \
                  len(self._content.get_children()) > 0
        self._separator.props.visible = visible

    def _update_accept_focus(self):
        accept_focus = len(self._content.get_children())
        if self.window:
            self.window.set_accept_focus(accept_focus)

    def _realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self._update_accept_focus()

    def _in_screen(self, x, y):
        [width, height] = self._full_request
        screen_area = self._invoker.get_screen_area()

        return x >= screen_area.x and \
               y >= screen_area.y and \
               x + width <= screen_area.width and \
               y + height <= screen_area.height

    def _get_position(self, palette_halign, palette_valign,
                      invoker_halign, invoker_valign, inv_rect=None):
        if inv_rect == None:
            inv_rect = self._invoker.get_rect()

        palette_width, palette_height = self.size_request()

        x = inv_rect.x + inv_rect.width * invoker_halign + \
            palette_width * palette_halign

        y = inv_rect.y + inv_rect.height * invoker_valign + \
            palette_height * palette_valign

        return int(x), int(y)

    def _get_left_position(self, inv_rect=None):
        x, y = self._get_position(-1.0, 0.0, 0.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, -1.0, 0.0, 1.0, inv_rect)
        return x, y

    def _get_right_position(self, inv_rect=None):
        x, y = self._get_position(0.0, 0.0, 1.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(0.0, -1.0, 1.0, 1.0, inv_rect)
        return x, y

    def _get_top_position(self, inv_rect=None):
        x, y = self._get_position(0.0, -1.0, 0.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, -1.0, 1.0, 0.0, inv_rect)
        return x, y

    def _get_bottom_position(self, inv_rect=None):
        x, y = self._get_position(0.0, 0.0, 0.0, 1.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, 0.0, 1.0, 1.0, inv_rect)
        return x, y

    def _get_around_position(self, inv_rect=None):
        x, y = self._get_bottom_position(inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_right_position(inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_top_position(inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_left_position(inv_rect)

        return x, y

    def _get_at_cursor_position(self, inv_rect=None):
        x, y = self._get_position(0.0, 0.0, 1.0, 1.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(0.0, -1.0, 1.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, -1.0, 0.0, 0.0, inv_rect)
        if not self._in_screen(x, y):
            x, y = self._get_position(-1.0, 0.0, 0.0, 1.0, inv_rect)

        return x, y

    def _update_full_request(self):
        state = self._state

        self.set_size_request(-1, -1)

        self._set_state(self._SECONDARY)
        self._full_request = self.size_request()

        self.set_size_request(self._full_request[0], -1)

        self._set_state(state)

    def _update_cursor_position(self):
        display = gtk.gdk.display_get_default()
        screen, x, y, mask = display.get_pointer()
        self._cursor_x = x
        self._cursor_y = y

    def _update_position(self):
        x = y = 0

        if self._position == self.DEFAULT:
            position = self._invoker.get_default_position()
        else:
            position = self._position

        if position == self.AT_CURSOR:
            dist = style.PALETTE_CURSOR_DISTANCE
            rect = gtk.gdk.Rectangle(self._cursor_x - dist,
                                     self._cursor_y - dist,
                                     dist * 2, dist * 2)

            x, y = self._get_at_cursor_position(rect)
        elif position == self.AROUND:
            x, y = self._get_around_position()
        elif position == self.BOTTOM:
            x, y = self._get_bottom_position()
        elif position == self.LEFT:
            x, y = self._get_left_position()
        elif position == self.RIGHT:
            x, y = self._get_right_position()
        elif position == self.TOP:
            x, y = self._get_top_position()

        self.move(x, y)

    def _show(self):
        if self._up:
            return

        self._update_cursor_position()        
        self._update_full_request()

        self._palette_popup_sid = _palette_observer.connect(
                                'popup', self._palette_observer_popup_cb)

        self._update_position()
        self.menu.set_active(True)
        self.show()

        if self._invoker:
            self._invoker.notify_popup()

        self._up = True
        _palette_observer.emit('popup', self)
        self.emit('popup')

    def _hide(self):
        if not self._palette_popup_sid is None:
            _palette_observer.disconnect(self._palette_popup_sid)
            self._palette_popup_sid = None

        self.menu.set_active(False)
        self.hide()

        if self._invoker:
            self._invoker.notify_popdown()

        self._up = False
        self.emit('popdown')

    def popup(self):
        self._popdown_anim.stop()
        self._popup_anim.start()
        self._secondary_anim.start()

    def popdown(self, inmediate=False):
        self._secondary_anim.stop()
        self._popup_anim.stop()

        if not inmediate:
            self._popdown_anim.start()
        else:
            self._hide()

    def _set_state(self, state):
        if self._state == state:
            return

        if state == self._PRIMARY:
            self.menu.unembed()
            self._secondary_box.hide()
        elif state == self._SECONDARY:
            self.menu.embed(self._menu_box)
            self._secondary_box.show()

        self._state = state

    def _invoker_mouse_enter_cb(self, invoker):
        self.popup()

    def _invoker_mouse_leave_cb(self, invoker):
        self.popdown()

    def _enter_notify_event_cb(self, widget, event):
        if event.detail != gtk.gdk.NOTIFY_INFERIOR:
            self._popdown_anim.stop()
            self._secondary_anim.start()

    def _leave_notify_event_cb(self, widget, event):
        if event.detail != gtk.gdk.NOTIFY_INFERIOR:
            self.popdown()

    def _palette_observer_popup_cb(self, observer, palette):
        if self != palette:
            self._hide()

class PaletteActionBar(gtk.HButtonBox):
    def add_action(label, icon_name=None):
        button = Button(label)

        if icon_name:
            icon = Icon(icon_name)
            button.set_image(icon)
            icon.show()

        self.pack_start(button)
        button.show()

class _Menu(_sugaruiext.Menu):
    __gtype_name__ = 'SugarPaletteMenu'

    def __init__(self, palette):
        _sugaruiext.Menu.__init__(self)
        self._palette = palette

    def do_insert(self, item, position):
        _sugaruiext.Menu.do_insert(self, item, position)
        self._palette._update_separator()

    def do_expose_event(self, event):
        # Ignore the Menu expose, just do the MenuShell expose to prevent any
        # border from being drawn here. A border is drawn by the palette object
        # around everything.
        gtk.MenuShell.do_expose_event(self, event)

    def do_grab_notify(self, was_grabbed):
        # Ignore grab_notify as the menu would close otherwise
        pass

    def do_deactivate(self):
        self._palette._hide()

class _PopupAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._set_state(Palette._PRIMARY)
            self._palette._show()

class _SecondaryAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._set_state(Palette._SECONDARY)
            self._palette._update_position()

class _PopdownAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._hide()

class Invoker(gobject.GObject):
    __gtype_name__ = 'SugarPaletteInvoker'

    __gsignals__ = {
        'mouse-enter': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'mouse-leave': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'focus-out':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

    def has_rectangle_gap(self):
        return False

    def draw_rectangle(self, event, palette):
        pass

    def get_default_position(self):
        return Palette.AROUND

    def get_screen_area(self):
        width = gtk.gdk.screen_width()
        height = gtk.gdk.screen_height()
        return gtk.gdk.Rectangle(0, 0, width, height)

    def notify_popup(self):
        pass

    def notify_popdown(self):
        pass

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

    def has_rectangle_gap(self):
        return True

    def draw_rectangle(self, event, palette):
        style = self._widget.style
        gap = _calculate_gap(self.get_rect(), palette.get_rect())
        if gap:
            style.paint_box_gap(event.window, gtk.STATE_PRELIGHT,
                                gtk.SHADOW_IN, event.area, self._widget,
                                "palette-invoker",
                                self._widget.allocation.x,
                                self._widget.allocation.y,
                                self._widget.allocation.width,
                                self._widget.allocation.height,
                                gap[0], gap[1], gap[2])
        else:
            style.paint_box(event.window, gtk.STATE_PRELIGHT,
                            gtk.SHADOW_IN, event.area, self._widget,
                            "palette-invoker",
                            self._widget.allocation.x,
                            self._widget.allocation.y,
                            self._widget.allocation.width,
                            self._widget.allocation.height)

    def _enter_notify_event_cb(self, widget, event):
        self.emit('mouse-enter')

    def _leave_notify_event_cb(self, widget, event):
        self.emit('mouse-leave')

    def get_toplevel(self):
        return self._widget.get_toplevel()

    def notify_popup(self):
        self._widget.queue_draw()

    def notify_popdown(self):
        self._widget.queue_draw()

class CanvasInvoker(Invoker):
    def __init__(self, item):
        Invoker.__init__(self)
        self._item = item

        item.connect('motion-notify-event',
                     self._motion_notify_event_cb)

    def get_default_position(self):
        return Palette.AT_CURSOR

    def get_rect(self):
        context = self._item.get_context()
        if context:
            x, y = context.translate_to_screen(self._item)

        width, height = self._item.get_allocation()

        return gtk.gdk.Rectangle(x, y, width, height)

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            self.emit('mouse-enter')
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.emit('mouse-leave')

        return False

    def get_toplevel(self):
        return hippo.get_canvas_for_item(self._item).get_toplevel()

class _PaletteObserver(gobject.GObject):
    __gtype_name__ = 'SugarPaletteObserver'

    __gsignals__ = {
        'popup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

_palette_observer = _PaletteObserver()
