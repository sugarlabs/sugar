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

import math

import hippo

from sugar.graphics.color import Color

class Frame(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarFrame'

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        self._line_width = 3.0
        self._radius = 30
        self._border_color = Color.FRAME_BORDER

    def do_paint_below_children(self, cr, damaged_box):
        [width, height] = self.get_allocation()

        x = self._line_width
        y = self._line_width
        width -= self._line_width * 2
        height -= self._line_width * 2

        cr.move_to(x + self._radius, y);
        cr.arc(x + width - self._radius, y + self._radius,
               self._radius, math.pi * 1.5, math.pi * 2);
        cr.arc(x + width - self._radius, x + height - self._radius,
               self._radius, 0, math.pi * 0.5);
        cr.arc(x + self._radius, y + height - self._radius,
               self._radius, math.pi * 0.5, math.pi);
        cr.arc(x + self._radius, y + self._radius, self._radius,
               math.pi, math.pi * 1.5);

        cr.set_source_rgba(*self._border_color.get_rgba())
        cr.set_line_width(self._line_width)
        cr.stroke()
