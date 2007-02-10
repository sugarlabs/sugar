# Copyright (C) 2007, One Laptop Per Child
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
import math
import logging

import gobject
import gtk
import hippo

from sugar.graphics.frame import Frame
from sugar.graphics.color import Color

class Entry(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarEntry'

    __gproperties__ = {
        'text'    : (str, None, None, None,
                      gobject.PARAM_READWRITE)
    }

    _BORDER_WIDTH = 3
    
    def __init__(self):
        hippo.CanvasBox.__init__(self)

        self._radius = -1

        self._entry = gtk.Entry()
        self._entry.props.has_frame = False
        self._update_colors(focused=False)
        self._entry.modify_text(gtk.STATE_SELECTED,
                                Color.BLACK.get_gdk_color())
        self._entry.connect('focus-in-event', self._entry_focus_in_event_cb)
        self._entry.connect('focus-out-event', self._entry_focus_out_event_cb)
                
        self._canvas_widget = hippo.CanvasWidget()
        self._canvas_widget.props.widget = self._entry
        self.append(self._canvas_widget, hippo.PACK_EXPAND)

    def do_set_property(self, pspec, value):
        if pspec.name == 'text':
            self._entry.set_text(value)

    def do_get_property(self, pspec, value):
        if pspec.name == 'text':
            return self._entry.get_text()

    def do_paint_below_children(self, cr, damaged_box):
        [width, height] = self._canvas_widget.get_allocation()
        
        x = self.props.padding_left
        y = self.props.padding_top - self._BORDER_WIDTH / 2

        cr.move_to(x, y - self._BORDER_WIDTH / 2);
        cr.arc(x + width + self._BORDER_WIDTH / 2, y - self._BORDER_WIDTH / 2 + self._radius,
               self._radius, math.pi * 1.5, math.pi * 0.5)
        cr.arc(x, y + self._radius - self._BORDER_WIDTH / 2, self._radius,
               math.pi * 0.5, math.pi * 1.5)

        cr.set_source_rgba(*self._background_color.get_rgba())
        cr.fill_preserve();

        cr.set_line_width(self._BORDER_WIDTH)        
        cr.set_source_rgba(*Color.ENTRY_BORDER.get_rgba())
        cr.stroke()

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [w_width, w_height] = self._canvas_widget.get_request()
        radius = min(w_width, w_height) / 2 + self._BORDER_WIDTH
        if radius != self._radius:
            self._radius = radius
            self.props.padding_top = height / 2 - w_height / 2 - self._BORDER_WIDTH / 2
            self.props.padding_left = self._radius + self._BORDER_WIDTH / 2
            self.props.padding_right = self._radius + self._BORDER_WIDTH / 2
        
        # Make the entry expand horizontally
        w_width = width - (self.props.padding_left + self.props.padding_right)
        
        self._canvas_widget.do_allocate(self._canvas_widget, w_width, w_height,
                                        origin_changed)

    def _entry_focus_in_event_cb(self, widget, event):
        self._update_colors(focused=True)
        self.emit_paint_needed(0, 0, -1, -1)

    def _entry_focus_out_event_cb(self, widget, event):
        self._update_colors(focused=False)
        self.emit_paint_needed(0, 0, -1, -1)

    def _update_colors(self, focused):
        if focused:
            self._background_color = Color.ENTRY_BACKGROUND_FOCUSED

            self._entry.modify_base(gtk.STATE_NORMAL,
                                    Color.ENTRY_BACKGROUND_FOCUSED.get_gdk_color())
            self._entry.modify_base(gtk.STATE_SELECTED,
                                    Color.ENTRY_SELECTION_FOCUSED.get_gdk_color())
            self._entry.modify_text(gtk.STATE_NORMAL,
                                    Color.ENTRY_TEXT_FOCUSED.get_gdk_color())
        else:
            self._background_color = Color.ENTRY_BACKGROUND_UNFOCUSED
        
            self._entry.modify_base(gtk.STATE_NORMAL,
                                    Color.ENTRY_BACKGROUND_UNFOCUSED.get_gdk_color())
            self._entry.modify_base(gtk.STATE_SELECTED,
                                    Color.ENTRY_SELECTION_UNFOCUSED.get_gdk_color())
            self._entry.modify_text(gtk.STATE_NORMAL,
                                    Color.ENTRY_TEXT_UNFOCUSED.get_gdk_color())
