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

import sys

import gobject
import hippo

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.roundbox import RoundBox
from sugar.graphics import units
from sugar.graphics import color
from sugar.graphics import font

class Button(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarButton'

    __gproperties__ = {
        'active'    : (bool, None, None, True,
                       gobject.PARAM_READWRITE),
        'icon-name' : (str, None, None, None,
                       gobject.PARAM_READWRITE),
        'text'      : (str, None, None, None,
                       gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._active = True
        self._icon = None

        self._round_box = RoundBox()
        self._round_box.props.border_color = color.BLACK.get_int()
        self._round_box.props.background_color = color.BLACK.get_int()
        self._round_box.props.padding_top = units.points_to_pixels(1)
        self._round_box.props.padding_bottom = units.points_to_pixels(1)
        
        self._text_box = hippo.CanvasText()
        self._text_box.props.font_desc = font.DEFAULT.get_pango_desc()
        self._text_box.props.color = color.BUTTON_NORMAL.get_int()
        self._round_box.append(self._text_box)
        
        hippo.CanvasBox.__init__(self, **kwargs)
        self.props.yalign = hippo.ALIGNMENT_CENTER

        self.append(self._round_box)

        if not self.props.color:
            self.props.color = color.BUTTON_NORMAL.get_int()
        if not self.props.color:
            self.props.background_color = \
                color.BUTTON_BACKGROUND_NORMAL.get_int()

        self._normal_color = self.props.color
        self._normal_background_color = self.props.background_color
        
        self.connect('button-press-event',
                     self._button_button_press_event_cb)

    def do_set_property(self, pspec, value):
        if pspec.name == 'active':
            self._active = value
            if self._active:
                self.props.color = self._normal_color
                self.props.background_color = self._normal_background_color
            else:
                self.props.color = color.BUTTON_INACTIVE.get_int()
                self.props.background_color = \
                    color.BUTTON_BACKGROUND_INACTIVE.get_int()
        elif pspec.name == 'icon-name':
            if value:
                if self._icon:
                    self._icon.props.icon_name = value
                else:
                    self._icon = CanvasIcon(icon_name=value,
                                            scale=units.SMALL_ICON_SCALE,
                                            fill_color=color.WHITE,
                                            stroke_color=color.BLACK)
                    # Insert icon on the label's left
                    self._round_box.remove_all()
                    self._round_box.append(self._icon)
                    self._round_box.append(self._text_box)
            else:
                if self._icon:
                    self._round_box.remove(self._icon)
                    self._icon = None
        elif pspec.name == 'text':
            self._text_box.props.text = value
        else:
            hippo.CanvasBox.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'active':
            return self._active
        elif pspec.name == 'icon-name':
            if self._icon:
                return self._icon.props.icon_name
            else:
                return None
        elif pspec.name == 'text':
            return self._text_box.props.text
        else:
            return hippo.CanvasBox.do_get_property(self, pspec)

    def _button_button_press_event_cb(self, widget, event):
        if self._active:
            self.emit_activated()
        return True

    def prelight(self, enter):
        if enter:
            if self._active:
                self.props.background_color = color.BLACK.get_int()
        else:
            if self._active:
                self.props.background_color = self._normal_background_color
