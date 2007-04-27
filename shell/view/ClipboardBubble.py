# Copyright (C) 2006, Red Hat, Inc.
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

#TODO: has to be merged with all the existing bubbles in a generic progress bar widget

import math

import gobject
import gtk
import hippo

from sugar.graphics import units

class ClipboardBubble(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'ClipboardBubble'

    __gproperties__ = {
        'fill-color': (object, None, None,
                      gobject.PARAM_READWRITE),
        'stroke-color': (object, None, None,
                      gobject.PARAM_READWRITE),
        'progress-color': (object, None, None,
                      gobject.PARAM_READWRITE),
        'percent'   : (object, None, None,
                      gobject.PARAM_READWRITE),
    }

    def __init__(self, **kwargs):
        self._stroke_color = 0xFFFFFFFF
        self._fill_color = 0xFFFFFFFF
        self._progress_color = 0x000000FF
        self._percent = 0
        self._radius = units.points_to_pixels(3)

        hippo.CanvasBox.__init__(self, **kwargs)

    def do_set_property(self, pspec, value):
        if pspec.name == 'fill-color':
            self._fill_color = value
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'stroke-color':
            self._stroke_color = value
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'progress-color':
            self._progress_color = value
            self.emit_paint_needed(0, 0, -1, -1)
        elif pspec.name == 'percent':
            self._percent = value
            self.emit_paint_needed(0, 0, -1, -1)

    def do_get_property(self, pspec):
        if pspec.name == 'fill-color':
            return self._fill_color
        elif pspec.name == 'stroke-color':
            return self._stroke_color
        elif pspec.name == 'progress-color':
            return self._progress_color
        elif pspec.name == 'percent':
            return self._percent

    def _int_to_rgb(self, int_color):
        red = (int_color >> 24) & 0x000000FF
        green = (int_color >> 16) & 0x000000FF
        blue = (int_color >> 8) & 0x000000FF
        alpha = int_color & 0x000000FF
        return (red / 255.0, green / 255.0, blue / 255.0)

    def do_paint_below_children(self, cr, damaged_box):
        [width, height] = self.get_allocation()

        line_width = 3.0
        x = line_width
        y = line_width
        width -= line_width * 2
        height -= line_width * 2

        cr.move_to(x + self._radius, y);
        cr.arc(x + width - self._radius, y + self._radius,
               self._radius, math.pi * 1.5, math.pi * 2);
        cr.arc(x + width - self._radius, x + height - self._radius,
               self._radius, 0, math.pi * 0.5);
        cr.arc(x + self._radius, y + height - self._radius,
               self._radius, math.pi * 0.5, math.pi);
        cr.arc(x + self._radius, y + self._radius, self._radius,
               math.pi, math.pi * 1.5);

        color = self._int_to_rgb(self._fill_color)
        cr.set_source_rgb(*color)
        cr.fill_preserve();

        color = self._int_to_rgb(self._stroke_color)
        cr.set_source_rgb(*color)
        cr.set_line_width(line_width)
        cr.stroke();

        if self._percent > 0:
            self._paint_progress_bar(cr, x, y, width, height, line_width)

    def _paint_progress_bar(self, cr, x, y, width, height, line_width):
        prog_x = x + line_width
        prog_y = y + line_width
        prog_width = (width - (line_width * 2)) * (self._percent / 100.0)
        prog_height = (height - (line_width * 2))

        x = prog_x
        y = prog_y
        width = prog_width
        height = prog_height

        cr.move_to(x + self._radius, y);
        cr.arc(x + width - self._radius, y + self._radius,
               self._radius, math.pi * 1.5, math.pi * 2);
        cr.arc(x + width - self._radius, x + height - self._radius,
               self._radius, 0, math.pi * 0.5);
        cr.arc(x + self._radius, y + height - self._radius,
               self._radius, math.pi * 0.5, math.pi);
        cr.arc(x + self._radius, y + self._radius, self._radius,
               math.pi, math.pi * 1.5);

        color = self._int_to_rgb(self._progress_color)
        cr.set_source_rgb(*color)
        cr.fill_preserve();
