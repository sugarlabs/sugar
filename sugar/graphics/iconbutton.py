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
from sugar.graphics import units
from sugar.graphics import color
            
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

        if self._active:
            self.props.fill_color = color.BUTTON_BACKGROUND_NORMAL
            self.props.stroke_color = color.BUTTON_NORMAL
            self.props.background_color = \
                color.BUTTON_BACKGROUND_NORMAL.get_int()
        else:
            self.props.fill_color = color.BUTTON_BACKGROUND_INACTIVE
            self.props.stroke_color = color.BUTTON_INACTIVE
            self.props.background_color = \
                color.BUTTON_BACKGROUND_INACTIVE.get_int()

        self._set_size(STANDARD_SIZE)

        self.connect('button-press-event',
                     self._icon_button_button_press_event_cb)

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
                self.props.fill_color = color.BUTTON_BACKGROUND_NORMAL
                self.props.stroke_color = color.BUTTON_NORMAL
            else:
                self.props.fill_color = color.BUTTON_BACKGROUND_INACTIVE
                self.props.stroke_color = color.BUTTON_INACTIVE
        else:
            CanvasIcon.do_set_property(self, pspec, value)

    def do_get_property(self, pspec):
        if pspec.name == 'size':
            return self._size
        elif pspec.name == 'active':
            return self._active
        else:
            return CanvasIcon.do_get_property(self, pspec)

    def _icon_button_button_press_event_cb(self, widget, event):
        if self._active:
            self.emit_activated()
        return True

    def prelight(self, enter):
        if enter:
            if self._active:
                self.props.background_color = color.BLACK.get_int()
        else:
            self.props.background_color = \
                color.BUTTON_BACKGROUND_NORMAL.get_int()
