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

from sugar.graphics import units
from sugar.graphics import color

class RoundBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarRoundBox'

    _BORDER_DEFAULT = 2.0

    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        # TODO: we should calculate this value depending on the height of the box.
        self._radius = units.points_to_pixels(7)
        
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL
        self.props.border_top = self._BORDER_DEFAULT
        self.props.border_bottom = self._BORDER_DEFAULT
        self.props.border_left = self._radius
        self.props.border_right = self._radius
        self.props.border_color = color.BLACK.get_int()
            
    def do_paint_background(self, cr, damaged_box):
        [width, height] = self.get_allocation()

        x = self._BORDER_DEFAULT / 2
        y = self._BORDER_DEFAULT / 2
        width -= self._BORDER_DEFAULT
        height -= self._BORDER_DEFAULT

        cr.move_to(x + self._radius, y);
        cr.arc(x + width - self._radius, y + self._radius,
               self._radius, math.pi * 1.5, math.pi * 2);
        cr.arc(x + width - self._radius, x + height - self._radius,
               self._radius, 0, math.pi * 0.5);
        cr.arc(x + self._radius, y + height - self._radius,
               self._radius, math.pi * 0.5, math.pi);
        cr.arc(x + self._radius, y + self._radius, self._radius,
               math.pi, math.pi * 1.5);

        hippo.cairo_set_source_rgba32(cr, self.props.background_color)
        cr.fill_preserve();

        hippo.cairo_set_source_rgba32(cr, self.props.border_color)
        cr.set_line_width(self._BORDER_DEFAULT)
        cr.stroke()
