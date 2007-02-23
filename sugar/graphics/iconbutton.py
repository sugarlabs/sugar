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

from canvasicon import CanvasIcon
from xocolor import XoColor
from sugar.graphics import units
from sugar import profile
            
STANDARD_SIZE = 0
SMALL_SIZE    = 1

class IconButton(CanvasIcon):
    __gtype_name__ = 'SugarIconButton'    

    __gproperties__ = {
        'size'      : (int, None, None,
                       0, sys.maxint, STANDARD_SIZE,
                       gobject.PARAM_READWRITE),
        'active'    : (bool, None, None, True,
                       gobject.PARAM_READWRITE)
    }

    def __init__(self, **kwargs):
        self._active = True

        CanvasIcon.__init__(self, cache=True, **kwargs)

        if self.props.color:
            self._normal_color = self.props.color
        else:
            self._normal_color = XoColor('white')
            self.props.color = self._normal_color

        self._prelight_color = profile.get_color()
        self._inactive_color = XoColor('#808080,#424242')
        self._set_size(STANDARD_SIZE)

        self.connect('button-press-event', self._button_press_event_cb)

    def _set_size(self, size):
        if size == SMALL_SIZE:
            self.props.box_width = -1
            self.props.box_height = -1
            self.props.scale = units.SMALL_ICON_SCALE
        else:
            self.props.box_width = units.grid_to_pixels(1)
            self.props.box_height = units.grid_to_pixels(1)
            self.props.scale = units.STANDARD_ICON_SCALE

        self._size = size

    def do_set_property(self, pspec, value):
        if pspec.name == 'size':
            self._set_size(value)
        elif pspec.name == 'active':
            self._active = value
            if self._active:
                self.props.color = self._normal_color
            else:
                self.props.color = self._inactive_color            
        else:
            CanvasIcon.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'size':
            return self._size
        elif pspec.name == 'active':
            return self._active
        else:
            return CanvasIcon.do_get_property(self, pspec)

    def _button_press_event_cb(self, widget, event):
        if self._active:
            self.emit_activated()
        return True
