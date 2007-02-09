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

import hippo
import gtk

from sugar.graphics.frame import Frame
from sugar.graphics.color import Color

class Entry(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarEntry'
    
    def __init__(self):
        hippo.CanvasBox.__init__(self)

        self._radius = -1
        self._background_color = Color.ENTRY_BACKGROUND_UNFOCUSED

        self._entry = gtk.Entry()
        self._entry.props.has_frame = False
        self._entry.modify_base(gtk.STATE_NORMAL,
                                self._background_color.get_gdk_color())
        self._entry.connect('focus-in-event', self._entry_focus_in_event_cb)
        self._entry.connect('focus-out-event', self._entry_focus_out_event_cb)
        
        self._canvas_widget = hippo.CanvasWidget()
        self._canvas_widget.props.widget = self._entry
        self.append(self._canvas_widget, hippo.PACK_EXPAND)

    def do_paint_below_children(self, cr, damaged_box):
        logging.debug('do_paint_below_children: %s', str(self._background_color))

        [width, height] = self._canvas_widget.get_allocation()

        x = 0
        y = 0

        cr.move_to(x + self._radius, y);
        cr.arc(x + width - self._radius, y + self._radius,
               self._radius, math.pi * 1.5, math.pi * 2);
        cr.arc(x + width - self._radius, x + height - self._radius,
               self._radius, 0, math.pi * 0.5);
        cr.arc(x + self._radius, y + height - self._radius,
               self._radius, math.pi * 0.5, math.pi);
        cr.arc(x + self._radius, y + self._radius, self._radius,
               math.pi, math.pi * 1.5);

        cr.set_source_rgba(*self._background_color.get_rgba())
        cr.fill_preserve();

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [width, height] = self._canvas_widget.get_request()
        radius = min(width, height) / 2
        if radius != self._radius:
            self._radius = radius
            self._canvas_widget.props.padding_left = self._radius
            self._canvas_widget.props.padding_right = self._radius

        self._canvas_widget.do_allocate(self._canvas_widget, width, height,
                                       origin_changed)

    def _entry_focus_in_event_cb(self, widget, event):
        self._background_color = Color.ENTRY_BACKGROUND_FOCUSED
        self._entry.modify_base(gtk.STATE_NORMAL,
                                self._background_color.get_gdk_color())
        self.emit_paint_needed(0, 0, -1, -1)
        logging.debug('_entry_focus_in_event_cb')

    def _entry_focus_out_event_cb(self, widget, event):
        self._background_color = Color.ENTRY_BACKGROUND_UNFOCUSED
        self._entry.modify_base(gtk.STATE_NORMAL,
                                self._background_color.get_gdk_color())
        self.emit_paint_needed(0, 0, -1, -1)
        logging.debug('_entry_focus_out_event_cb')
