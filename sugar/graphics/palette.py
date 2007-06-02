#!/usr/bin/env python

# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com)
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
from gtk import gdk, keysyms
import gobject
import pango

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
        'parent': (object, None, None, gobject.PARAM_READWRITE),

        'alignment': (gobject.TYPE_INT, None, None, 0, 8, ALIGNMENT_AUTOMATIC,
                    gobject.PARAM_READWRITE),
        
        'is-tooltip': (bool, None, None, False, gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY)
    }

    _PADDING    = 1
    _WIN_BORDER = 5

    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, type=gtk.WINDOW_POPUP, **kwargs)
        gtk.Window.__init__(self)

        self._alignment = ALIGNMENT_AUTOMATIC

        self._palette_label = gtk.Label()
        #self._palette_label.set_justify(gtk.JUSTIFY_LEFT)
        self._palette_label.show()

        vbox = gtk.VBox(False, 0)
        vbox.pack_start(self._palette_label, True, True, self._PADDING)

        # If it's a tooltip palette..
        if not self._is_tooltip:
            self._separator = gtk.HSeparator()
            self._separator.hide()
    
            self._menu_bar = gtk.MenuBar()
            self._menu_bar.set_pack_direction(gtk.PACK_DIRECTION_TTB)
            self._menu_bar.show()
    
            self._content = gtk.HBox()
            self._content.show()
    
            self._button_bar = gtk.HButtonBox()
            self._button_bar.show()
    
            # Set main container
            vbox.pack_start(self._separator, True, True, self._PADDING)
            vbox.pack_start(self._menu_bar, True, True, self._PADDING)
            vbox.pack_start(self._content, True, True, self._PADDING)
            vbox.pack_start(self._button_bar, True, True, self._PADDING)
        
        vbox.show()
        self.add(vbox)

        # Widget events
        self.connect('motion-notify-event', self._mouse_over_widget_cb)
        self.connect('leave-notify-event', self._mouse_out_widget_cb)
        self.connect('button-press-event', self._close_palette_cb)
        self.connect('key-press-event', self._on_key_press_event_cb)

        self.set_border_width(self._WIN_BORDER)

    def do_set_property(self, pspec, value):
        if pspec.name == 'parent':
            self._parent_widget = value
        elif pspec.name == 'alignment':
            self._alignment = value
        elif pspec.name == 'is-tooltip':
            self._is_tooltip = value
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
        scr_width = gtk.gdk.screen_width()
        scr_height = gtk.gdk.screen_height()

        plt_width, plt_height = self.size_request()

        move_x, move_y = self._calc_position(alignment)
        self.move(move_x, move_y)
        plt_x, plt_y = self.window.get_origin()

        if (plt_x<0 or plt_x+plt_width>scr_width) or (plt_y<0 or plt_y+plt_height>scr_height):
            return False
        else:
            self.move(move_x, move_y)
            return True

    def _calc_position(self, alignment):
        win_x, win_y = self._parent_widget.window.get_origin()
        parent_rectangle = self._parent_widget.get_allocation()
        palette_rectangle = self.get_allocation()

        palette_width, palette_height = self.size_request()

        if alignment == ALIGNMENT_BOTTOM_LEFT:
            move_x = win_x + parent_rectangle.x
            move_y = win_y + parent_rectangle.y + parent_rectangle.height

        elif alignment == ALIGNMENT_BOTTOM_RIGHT:
            move_x = (win_x + parent_rectangle.x + parent_rectangle.width) - palette_width
            move_y = win_y + parent_rectangle.y + parent_rectangle.height

        elif alignment == ALIGNMENT_LEFT_BOTTOM:
            move_x = (win_x + parent_rectangle.x) - palette_width
            move_y = win_y + parent_rectangle.y

        elif alignment == ALIGNMENT_LEFT_TOP:
            move_x = (win_x + parent_rectangle.x) - palette_width
            move_y = (win_y + parent_rectangle.y + parent_rectangle.height) - palette_rectangle.height 

        elif alignment == ALIGNMENT_RIGHT_BOTTOM:
            move_x = win_x + parent_rectangle.x + parent_rectangle.width
            move_y = win_y + parent_rectangle.y

        elif alignment == ALIGNMENT_RIGHT_TOP:
            move_x = win_x + parent_rectangle.x + parent_rectangle.width
            move_y = (win_y + parent_rectangle.y + parent_rectangle.height) - palette_rectangle.height

        elif alignment == ALIGNMENT_TOP_LEFT:
            move_x = (win_x + parent_rectangle.x)
            move_y = (win_y + parent_rectangle.y) - (palette_rectangle.height)

        elif alignment == ALIGNMENT_TOP_RIGHT:
            move_x = (win_x + parent_rectangle.x + parent_rectangle.width) - palette_width
            move_y = (win_y + parent_rectangle.y) - (palette_rectangle.height)

        return move_x, move_y

    def set_primary_state(self, label, accel_path=None):
        if accel_path != None:
            item = gtk.MenuItem(label)
            item.set_accel_path(accel_path)
            self.append_menu_item(item)
            self._separator.hide()
        else:
            self._palette_label.set_text(label)
            if not self._is_tooltip:
                self._separator.show()

    def append_menu_item(self, item):
        self._menu_bar.append(item)
        item.show()

    def set_content(self, widget):
        self._content.pack_start(widget, True, True, self._PADDING)
        widget.show()

    def append_button(self, button):
        button.connect('released', self._close_palette_cb)
        self._button_bar.pack_start(button, True, True, self._PADDING)
        button.show()

    # Display the palette and set the position on the screen
    def popup(self):
        # We need to know if the mouse pointer continue inside
        # the parent widget (opener)
        pointer_x, pointer_y = self._parent_widget.get_pointer()
        parent_alloc = self._parent_widget.get_allocation()
        pointer_rect = gdk.Rectangle(pointer_x + parent_alloc.x, pointer_y + parent_alloc.y, 1, 1)

        if (self._parent_widget.allocation.intersect(pointer_rect).width == 0):
            return

        self.show()
        self.set_position()
        self._pointer_grab()

    # PRIVATE METHODS

    def _is_mouse_out(self, window, event):
        # If we're clicking outside of the Palette
        # return True
        event_rect = gdk.Rectangle(int(event.x), int(event.y), 1, 1)

        if (event.window != self.window or self.allocation.intersect(event_rect).width==0):
            return True
        else:
            return False

    def _pointer_grab(self):
        gtk.gdk.pointer_grab(self.window, owner_events=False,
            event_mask=gtk.gdk.BUTTON_PRESS_MASK |
            gtk.gdk.BUTTON_RELEASE_MASK |
            gtk.gdk.ENTER_NOTIFY_MASK |
            gtk.gdk.LEAVE_NOTIFY_MASK |
            gtk.gdk.POINTER_MOTION_MASK)

        gdk.keyboard_grab(self.window, False)

    # SIGNAL HANDLERS

    # Release the GDK pointer and hide the palette
    def _close_palette_cb(self, widget=None, event=None):
        gtk.gdk.pointer_ungrab()
        self.hide()

    # Mouse is out of the widget
    def _mouse_out_widget_cb(self, widget, event):
        if (widget == self) and self._is_mouse_out(widget, event):
            self._pointer_grab()

    # Mouse inside the widget
    def _mouse_over_widget_cb(self, widget, event):
        gtk.gdk.pointer_ungrab()

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
        elif keyval == keysyms.Tab:
            self._close_palette_cb()
