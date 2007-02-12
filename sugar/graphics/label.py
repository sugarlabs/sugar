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
import pango

from sugar.graphics import style
from sugar.graphics.roundbox import RoundBox
from sugar.graphics.button import Button
from sugar.graphics.color import Color

class Label(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarLabel'

    __gproperties__ = {
        'text'    : (str, None, None, None,
                      gobject.PARAM_READWRITE)
    }

    __gsignals__ = {
        'button-activated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([int]))
    }
    
    def __init__(self, text):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)
        self.props.yalign = hippo.ALIGNMENT_CENTER

        self._buttons = {}
        self._text = text

        self._round_box = RoundBox()
        self._round_box.props.border_color = Color.FRAME_BORDER.get_int()
        self.append(self._round_box, hippo.PACK_EXPAND)

        self._canvas_text = hippo.CanvasText()
        self._canvas_text.props.text = self._text
        self._canvas_text.props.color = Color.LABEL_TEXT.get_int()
        
        fd = pango.FontDescription()
        fd.set_size(int(round(style.default_font_size * pango.SCALE)))        
        self._canvas_text.props.font_desc = fd

        self._round_box.append(self._canvas_text, hippo.PACK_EXPAND)

    def add_button(self, icon_name, action_id):
        button = Button(icon_name=icon_name)

        button.props.scale = style.small_icon_scale
        
        button.props.yalign = hippo.ALIGNMENT_CENTER
        button.props.xalign = hippo.ALIGNMENT_START
        
        button.connect('activated', self._button_activated_cb)
        self._round_box.append(button)
        self._buttons[button] = action_id

    def _button_activated_cb(self, button):
        self.emit('button-activated', self._buttons[button])
