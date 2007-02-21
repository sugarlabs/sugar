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

from sugar.graphics.roundbox import RoundBox
from sugar.graphics import color
from sugar.graphics import font

class Label(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarLabel'

    __gproperties__ = {
        'text'    : (str, None, None, None,
                      gobject.PARAM_READWRITE)
    }
    
    def __init__(self, text=None):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)
        self.props.yalign = hippo.ALIGNMENT_CENTER

        self._text = text

        self._round_box = RoundBox()
        self._round_box.props.border_color = color.FRAME_BORDER.get_int()
        self.append(self._round_box, hippo.PACK_EXPAND)

        self._canvas_text = hippo.CanvasText()
        self._canvas_text.props.text = self._text
        self._canvas_text.props.color = color.LABEL_TEXT.get_int()
        self._canvas_text.props.font_desc = font.DEFAULT.get_pango_desc()
        self._round_box.append(self._canvas_text, hippo.PACK_EXPAND)

    def do_set_property(self, pspec, value):
        self._canvas_text.set_property(pspec.name, value)

    def do_get_property(self, pspec):
        return self._canvas_text.get_property(pspec.name)
