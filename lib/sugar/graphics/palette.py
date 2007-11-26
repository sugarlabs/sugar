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
from sugar import _sugarext

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

class MouseSpeedDetector(gobject.GObject):

    __gsignals__ = {
        'motion-slow': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
        'motion-fast': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    _MOTION_SLOW = 1
    _MOTION_FAST = 2

    def __init__(self, parent, delay, thresh):
        """Create MouseSpeedDetector object,
            delay in msec
            threshold in pixels (per tick of 'delay' msec)"""

        gobject.GObject.__init__(self)

        self._threshold = thresh
        self._parent = parent
        self._delay = delay

        self._state = None

        self._timeout_hid = None

    def start(self):
        self._state = None
        self._mouse_pos = self._get_mouse_position()

        self._timeout_hid = gobject.timeout_add(self._delay, self._timer_cb)

    def stop(self):
        if self._timeout_hid is not None:
            gobject.source_remove(self._timeout_hid)
        self._state = None

    def _get_mouse_position(self):
        display = gtk.gdk.display_get_default()
        screen, x, y, mask = display.get_pointer()
        return (x, y)

    def _detect_motion(self):
        oldx, oldy = self._mouse_pos
        (x, y) = self._get_mouse_position()
        self._mouse_pos = (x, y)

        dist2 = (oldx - x)**2 + (oldy - y)**2
        if dist2 > self._threshold**2:
            return True
        else:
            return False

    def _timer_cb(self):
        motion = self._detect_motion()
        if motion and self._state != self._MOTION_FAST:
            self.emit('motion-fast')
            self._state = self._MOTION_FAST
        elif not motion and self._state != self._MOTION_SLOW:
            self.emit('motion-slow')
            self._state = self._MOTION_SLOW

        return True

class Palette(gtk.Window):
    PRIMARY = 0
    SECONDARY = 1

    __gtype_name__ = 'SugarPalette'

    __gproperties__ = {
        'invoker'    : (object, None, None,
                        gobject.PARAM_READWRITE)
    }

    __gsignals__ = {
        'popup' :   (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([])),
        'popdown' : (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE, ([]))
    }

    def __init__(self, label, accel_path=None, menu_after_content=False):
        gtk.Window.__init__(self)

        self.set_decorated(False)
        self.set_resizable(False)
        # Just assume xthickness and ythickness are the same
        self.set_border_width(self.style.xthickness)
        self.connect('realize', self._realize_cb)

        self.palette_state = self.PRIMARY

        self._alignment = None
        self._old_alloc = None
        self._full_request = [0, 0]
        self._cursor_x = 0
        self._cursor_y = 0
        self._invoker = None
        self._group_id = None
        self._up = False
        self._palette_popup_sid = None

        self._popup_anim = animator.Animator(0.3, 10)
        self._popup_anim.add(_PopupAnimation(self))

        self._secondary_anim = animator.Animator(1.0, 10)
        self._secondary_anim.add(_SecondaryAnimation(self))

        self._popdown_anim = animator.Animator(0.6, 10)
        self._popdown_anim.add(_PopdownAnimation(self))

        vbox = gtk.VBox()

        self._label = gtk.Label()
        self._label.set_size_request(-1, style.zoom(style.GRID_CELL_SIZE)
                                          - 2*self.get_border_width())
        self._label.set_alignment(0, 0.5)
        self._label.set_padding(style.DEFAULT_SPACING, 0)
        vbox.pack_start(self._label, False)

        self._secondary_box = gtk.VBox()
        vbox.pack_start(self._secondary_box)

        self._separator = gtk.HSeparator()
        self._secondary_box.pack_start(self._separator)

        self._menu_content_separator = gtk.HSeparator()

        if menu_after_content:
            self._add_content()
            self._secondary_box.pack_start(self._menu_content_separator)
            self._add_menu()
        else:
            self._add_menu()
            self._secondary_box.pack_start(self._menu_content_separator)
            self._add_content()

        self.action_bar = PaletteActionBar()
        self._secondary_box.pack_start(self.action_bar)
        self.action_bar.show()

        self.add(vbox)
        vbox.show()

        # The menu is not shown here until an item is added
        self.menu = _Menu(self)

        self.connect('enter-notify-event',
                     self._enter_notify_event_cb)
        self.connect('leave-notify-event',
                     self._leave_notify_event_cb)

        self.set_primary_text(label, accel_path)
        self.set_group_id('default')

        self._mouse_detector = MouseSpeedDetector(self, 200, 5)
        self._mouse_detector.connect('motion-slow', self._mouse_slow_cb)

    def _add_menu(self):
        self._menu_box = gtk.VBox()
        self._secondary_box.pack_start(self._menu_box)
        self._menu_box.show()

    def _add_content(self):
        # The content is not shown until a widget is added
        self._content = gtk.VBox()
        self._content.set_border_width(style.DEFAULT_SPACING)
        self._secondary_box.pack_start(self._content)

    def do_style_set(self, previous_style):
        # Prevent a warning from pygtk
        if previous_style is not None:
            gtk.Window.do_style_set(self, previous_style)
        self.set_border_width(self.style.xthickness)

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
        if label is not None:
            self._label.set_markup("<b>"+label+"</b>")
            self._label.show()

    def set_content(self, widget):
        if len(self._content.get_children()) > 0:
            self._content.remove(self._content.get_children()[0])

        if widget is not None:
            self._content.add(widget)
            self._content.show()
        else:
            self._content.hide()

        self._update_accept_focus()
        self._update_separators()

    def set_group_id(self, group_id):
        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            group.remove(self)
        if group_id:
            self._group_id = group_id
            group = palettegroup.get_group(group_id)
            group.add(self)

    def do_set_property(self, pspec, value):
        if pspec.name == 'invoker':
            if self._invoker is not None:
                self._invoker.disconnect(self._enter_invoker_hid)
                self._invoker.disconnect(self._leave_invoker_hid)

            self._invoker = value
            if value is not None:
                self._enter_invoker_hid = self._invoker.connect(
                    'mouse-enter', self._invoker_mouse_enter_cb)
                self._leave_invoker_hid = self._invoker.connect(
                    'mouse-leave', self._invoker_mouse_leave_cb)
        else:
            raise AssertionError

    def do_get_property(self, pspec):
        if pspec.name == 'invoker':
            return self._invoker
        else:
            raise AssertionError

    def do_size_request(self, requisition):
        gtk.Window.do_size_request(self, requisition)

        requisition.width = max(requisition.width, self._full_request[0])

        # Minimum width
        requisition.width = max(requisition.width,
                                style.zoom(style.GRID_CELL_SIZE*2))

    def do_size_allocate(self, allocation):
        gtk.Window.do_size_allocate(self, allocation)

        if self._old_alloc is None or \
           self._old_alloc.x != allocation.x or \
           self._old_alloc.y != allocation.y or \
           self._old_alloc.width != allocation.width or \
           self._old_alloc.height != allocation.height:
            self.queue_draw()

        # We need to store old allocation because when size_allocate
        # is called widget.allocation is already updated.
        # gtk.Window resizing is different from normal containers:
        # the X window is resized, widget.allocation is updated from
        # the configure request handler and finally size_allocate is called.
        self._old_alloc = allocation

    def do_expose_event(self, event):
        # We want to draw a border with a beautiful gap
        if self._invoker is not None and self._invoker.has_rectangle_gap():
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

    def _update_separators(self):
        visible = len(self.menu.get_children()) > 0 or  \
                  len(self._content.get_children()) > 0
        self._separator.props.visible = visible

        visible = len(self.menu.get_children()) > 0 and  \
                  len(self._content.get_children()) > 0
        self._menu_content_separator.props.visible = visible

    def _update_accept_focus(self):
        accept_focus = len(self._content.get_children())
        if self.window:
            self.window.set_accept_focus(accept_focus)

    def _realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self._update_accept_focus()

    def _update_full_request(self):
        state = self.palette_state

        self._set_state(self.SECONDARY)
        self._full_request = self.size_request()

        self._set_state(state)

    def _update_position(self):
        invoker = self._invoker
        if invoker is None or self._alignment is None:
            logging.error('Cannot update the palette position.')
            return

        rect = self.size_request()
        position = invoker.get_position_for_alignment(self._alignment, rect)
        if position is None:
            position = invoker.get_position(rect)

        self.move(position.x, position.y)

    def _show(self):
        if self._up:
            return

        self._palette_popup_sid = _palette_observer.connect(
                                'popup', self._palette_observer_popup_cb)

        if self._invoker is not None:
            self._update_full_request()
            self._alignment = self._invoker.get_alignment(self._full_request)
            self._update_position()

        self.menu.set_active(True)
        self.show()

        self._invoker.notify_popup()

        self._up = True
        _palette_observer.emit('popup', self)
        self.emit('popup')

    def _hide(self):
        self._secondary_anim.stop()

        if not self._palette_popup_sid is None:
            _palette_observer.disconnect(self._palette_popup_sid)
            self._palette_popup_sid = None

        self.menu.set_active(False)
        self.hide()

        if self._invoker:
            self._invoker.notify_popdown()

        self._up = False
        self.emit('popdown')

    def popup(self, immediate=False):
        self._popdown_anim.stop()

        if not immediate:
            self._popup_anim.start()
        else:
            self._show()

        self._secondary_anim.start()

    def popdown(self, immediate=False):
        self._popup_anim.stop()

        if not immediate:
            self._popdown_anim.start()
        else:
            self._hide()

    def _set_state(self, state):
        if self.palette_state == state:
            return

        if state == self.PRIMARY:
            self.menu.unembed()
            self._secondary_box.hide()
        elif state == self.SECONDARY:
            self.menu.embed(self._menu_box)
            self._secondary_box.show()

        self.palette_state = state

    def _invoker_mouse_enter_cb(self, invoker):
        self._mouse_detector.start()

    def _mouse_slow_cb(self, widget):
        self._mouse_detector.stop()
        self._palette_do_popup()

    def _palette_do_popup(self):
        immediate = False

        if self.is_up():
            self._popdown_anim.stop() 
            return

        if self._group_id:
            group = palettegroup.get_group(self._group_id)
            if group and group.is_up():
                self._set_state(self.PRIMARY)

                immediate = True
                group.popdown()

        self.popup(immediate=immediate)

    def _invoker_mouse_leave_cb(self, invoker):
        if self._mouse_detector is not None:
            self._mouse_detector.stop()
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

class _Menu(_sugarext.Menu):
    __gtype_name__ = 'SugarPaletteMenu'

    def __init__(self, palette):
        _sugarext.Menu.__init__(self)
        self._palette = palette

    def do_insert(self, item, position):
        _sugarext.Menu.do_insert(self, item, position)
        self._palette._update_separators()
        self.show()

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
            self._palette._set_state(Palette.PRIMARY)
            self._palette._show()

class _SecondaryAnimation(animator.Animation):
    def __init__(self, palette):
        animator.Animation.__init__(self, 0.0, 1.0)
        self._palette = palette

    def next_frame(self, current):
        if current == 1.0:
            self._palette._set_state(Palette.SECONDARY)
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

    ANCHORED = 0
    AT_CURSOR = 1

    BOTTOM = [(0.0, 0.0, 0.0, 1.0),
              (-1.0, 0.0, 1.0, 1.0)]
    RIGHT  = [(0.0, 0.0, 1.0, 0.0),
              (0.0, -1.0, 1.0, 1.0)]
    TOP    = [(0.0, -1.0, 0.0, 0.0),
              (-1.0, -1.0, 1.0, 0.0)]
    LEFT   = [(-1.0, 0.0, 0.0, 0.0),
              (-1.0, -1.0, 0.0, 1.0)]

    def __init__(self):
        gobject.GObject.__init__(self)

        self._screen_area = gtk.gdk.Rectangle(0, 0, gtk.gdk.screen_width(),
                                              gtk.gdk.screen_height())
        self._position_hint = self.ANCHORED
        self._cursor_x = -1
        self._cursor_y = -1

    def _get_position_for_alignment(self, alignment, palette_dim):
        palette_halign = alignment[0]
        palette_valign = alignment[1]
        invoker_halign = alignment[2]
        invoker_valign = alignment[3]

        if self._cursor_x == -1 or self._cursor_y == -1:
            display = gtk.gdk.display_get_default()
            screen, x, y, mask = display.get_pointer()
            self._cursor_x = x
            self._cursor_y = y

        if self._position_hint is self.ANCHORED:
            rect = self.get_rect()
        else:
            dist = style.PALETTE_CURSOR_DISTANCE
            rect = gtk.gdk.Rectangle(self._cursor_x - dist,
                                     self._cursor_y - dist,
                                     dist * 2, dist * 2)

        palette_width, palette_height = palette_dim

        x = rect.x + rect.width * invoker_halign + \
            palette_width * palette_halign

        y = rect.y + rect.height * invoker_valign + \
            palette_height * palette_valign

        return gtk.gdk.Rectangle(int(x), int(y),
                                 palette_width, palette_height)

    def _in_screen(self, rect):
        return rect.x >= self._screen_area.x and \
               rect.y >= self._screen_area.y and \
               rect.x + rect.width <= self._screen_area.width and \
               rect.y + rect.height <= self._screen_area.height

    def _get_alignments(self):
        if self._position_hint is self.AT_CURSOR:
            return [(0.0, 0.0, 1.0, 1.0),
                    (0.0, -1.0, 1.0, 0.0),
                    (-1.0, -1.0, 0.0, 0.0),
                    (-1.0, 0.0, 0.0, 1.0)]
        else:
            return self.BOTTOM + self.RIGHT + self.TOP + self.LEFT

    def get_position_for_alignment(self, alignment, palette_dim):
        rect = self._get_position_for_alignment(alignment, palette_dim)
        if self._in_screen(rect):
            return rect
        else:
            return None

    def get_position(self, palette_dim):
        for alignment in self._get_alignments():
            rect = self._get_position_for_alignment(alignment, palette_dim)
            if self._in_screen(rect):
                break

        return rect

    def get_alignment(self, palette_dim):
        for alignment in self._get_alignments():
            rect = self._get_position_for_alignment(alignment, palette_dim)
            if self._in_screen(rect):
                break

        return alignment

    def has_rectangle_gap(self):
        return False

    def draw_rectangle(self, event, palette):
        pass

    def notify_popup(self):
        pass

    def notify_popdown(self):
        self._cursor_x = -1
        self._cursor_y = -1

class WidgetInvoker(Invoker):
    def __init__(self, widget):
        Invoker.__init__(self)
        self._widget = widget

        widget.connect('enter-notify-event', self._enter_notify_event_cb)
        widget.connect('leave-notify-event', self._leave_notify_event_cb)

    def get_rect(self):
        allocation = self._widget.get_allocation()
        if self._widget.window is not None:
            x, y = self._widget.window.get_origin()
        else:
            logging.warning(
                "Trying to position palette with invoker that's not realized.")
            x = 0
            y = 0

        if self._widget.flags() & gtk.NO_WINDOW:
            x += allocation.x
            y += allocation.y

        width = allocation.width
        height = allocation.height

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
        Invoker.notify_popup(self)
        self._widget.queue_draw()

    def notify_popdown(self):
        Invoker.notify_popdown(self)
        self._widget.queue_draw()

class CanvasInvoker(Invoker):
    def __init__(self, item):
        Invoker.__init__(self)

        self._item = item
        self._position_hint = self.AT_CURSOR

        item.connect('motion-notify-event',
                     self._motion_notify_event_cb)

    def get_default_position(self):
        return self.AT_CURSOR

    def get_rect(self):
        context = self._item.get_context()
        if context:
            x, y = context.translate_to_screen(self._item)
            width, height = self._item.get_allocation()
            return gtk.gdk.Rectangle(x, y, width, height)
        else:
            return gtk.gdk.Rectangle()
        
    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            context = self._item.get_context()
            self.emit('mouse-enter')
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            self.emit('mouse-leave')

        return False

    def get_toplevel(self):
        return hippo.get_canvas_for_item(self._item).get_toplevel()

class ToolInvoker(WidgetInvoker):
    def __init__(self, widget):
        WidgetInvoker.__init__(self, widget.child)

    def _get_alignments(self):
        parent = self._widget.get_parent()
        if parent is None:
            return WidgetInvoker.get_alignments()

        if parent.get_orientation() is gtk.ORIENTATION_HORIZONTAL:
            return self.BOTTOM + self.TOP
        else:
            return self.LEFT + self.RIGHT

class _PaletteObserver(gobject.GObject):
    __gtype_name__ = 'SugarPaletteObserver'

    __gsignals__ = {
        'popup': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([object]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

_palette_observer = _PaletteObserver()
