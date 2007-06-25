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
from gtk import gdk, keysyms
import gobject
import time
import hippo

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
        self.connect('enter-notify-event', self._mouse_over_widget_cb)
        self.connect('leave-notify-event', self._mouse_out_widget_cb)
        self.connect('button-press-event', self._close_palette_cb)
        self.connect('key-press-event', self._on_key_press_event_cb)

        self.set_border_width(self._WIN_BORDER)
        
        self._scr_width = gtk.gdk.screen_width()
        self._scr_height = gtk.gdk.screen_height()

    def do_set_property(self, pspec, value):
        if pspec.name == 'invoker':
            self._invoker = value
        elif pspec.name == 'alignment':
            self._alignment = value
        else:
            raise AssertionError

    def set_position(self):
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
        move_x, move_y = self._calc_position(alignment)
        self._width, self._height = self.size_request()

        plt_x, plt_y = self.window.get_origin()

        if move_x > plt_x:
            plt_x += (move_x - plt_x)
        else:
            plt_x -= (plt_x - move_x)

        if move_y > plt_y:
            plt_y += (move_y - plt_y)
        else:
            plt_y -= (plt_y - move_y)

        if (plt_x < 0 or plt_x + self._width > self._scr_width) or \
           (plt_y < 0 or plt_y + self._height > self._scr_height):
            return False
        else:
            self.move(move_x, move_y)
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
        self._menu_bar.append(item)
        self._menu_bar.show()

    def set_content(self, widget):
        self._separator.show()
        self._content.pack_start(widget, True, True, self._PADDING)

    def append_button(self, button):
        self._separator.show()
        button.connect('released', self._close_palette_cb)
        self._button_bar.pack_start(button, True, True, self._PADDING)

    # Display the palette and set the position on the screen
    def popup(self):
        self.realize()
        self.set_position()
        self._pointer_ungrab()

    def popdown(self):
        self._pointer_ungrab()
        self.hide()

    # PRIVATE METHODS

    # Is the mouse out of the widget ?
    def _is_mouse_out(self, widget):
        mouse_x, mouse_y = widget.get_pointer()
        event_rect = gdk.Rectangle(mouse_x, mouse_y, 1, 1)

        if (self.allocation.intersect(event_rect).width==0):
            return True
        else:
            return False

    def _pointer_ungrab(self):
        gdk.keyboard_ungrab()

    def _pointer_grab(self):
        gdk.keyboard_grab(self.window, False)

    # SIGNAL HANDLERS

    # Release the GDK pointer and hide the palette
    def _close_palette_cb(self, widget=None, event=None):
        self.popdown()

    # Mouse is out of the widget
    def _mouse_out_widget_cb(self, widget, event):
        if (widget == self) and self._is_mouse_out(widget):
            self._close_palette_cb()
            return

        self._pointer_grab()

    # Mouse inside the widget
    def _mouse_over_widget_cb(self, widget, event):
        self._pointer_ungrab()

    # Some key is pressed
    def _on_key_press_event_cb(self, window, event):
        # Escape or Alt+Up: Close
        # Enter, Return or Space: Select
        keyval = event.keyval
        state = event.state & gtk.accelerator_get_default_mod_mask()

        if (keyval == keysyms.Escape or
            ((keyval == keysyms.Up or keyval == keysyms.KP_Up) and
             state == gdk.MOD1_MASK)):
            self._close_palette_cb()

class WidgetInvoker:
    def __init__(self, parent):
        self._parent = parent

    def get_rect(self):
        win_x, win_y = self._parent.window.get_origin()
        rectangle = self._parent.get_allocation()

        x = win_x + rectangle.x
        y = win_y + rectangle.y
        width = rectangle.width
        height = rectangle.height

        return gtk.gdk.Rectangle(x, y, width, height)

    # Is mouse over self._parent ?
    def is_mouse_over(self):
        pointer_x, pointer_y = self._parent.get_pointer()
        self._parent_alloc = self._parent.get_allocation()

        pointer_rect = gdk.Rectangle(pointer_x + self._parent_alloc.x, \
            pointer_y + self._parent_alloc.y, 1, 1)

        if (self._parent.allocation.intersect(pointer_rect).width == 0):
            return False

        return True

class CanvasInvoker:
    def __init__(self, parent):
        self._parent = parent

    def get_rect(self):
        context = self._parent.get_context()
        x, y = context.translate_to_screen(self._parent)
        width, height = self._parent.get_allocation()

        return gtk.gdk.Rectangle(x, y, width, height)

    # Is mouse over self._parent ?
    def is_mouse_over(self):
        return True
