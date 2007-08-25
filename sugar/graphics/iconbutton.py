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

#
# DEPRECATED. Do not use in new code. We will reimplement it in gtk
#

import sys

import gobject
import hippo

from sugar.graphics.icon import CanvasIcon
from sugar.graphics import style
            
class IconButton(CanvasIcon, hippo.CanvasItem):
    __gtype_name__ = 'SugarIconButton'    

    def __init__(self, **kwargs):
        CanvasIcon.__init__(self, cache=True, **kwargs)

        if not self.props.fill_color and not self.props.stroke_color:
            self.props.fill_color = style.Color("#404040")
            self.props.stroke_color = style.Color("#FFFFFF")

        self.connect('activated', self._icon_clicked_cb)

        self.props.box_width = style.GRID_CELL_SIZE
        self.props.box_height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE

    def do_button_press_event(self, event):
        if self._active:
            self.emit_activated()
        return True

    def prelight(self, enter):
        if enter:
            if self.props.active:
                self.props.background_color = 0x000000FF
        else:
            self.props.background_color = 0x00000000

    def _icon_clicked_cb(self, button):
        if self._palette:
            self._palette.popdown(True)
