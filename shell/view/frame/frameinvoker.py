# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
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

import gtk

from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.palette import CanvasInvoker

class FrameCanvasInvoker(CanvasInvoker):
    def __init__(self, item):
        CanvasInvoker.__init__(self, item)

    def get_default_position(self):
        return Palette.AROUND

    def get_screen_area(self):
        frame_thickness = style.zoom(75)

        x = y = frame_thickness
        width = gtk.gdk.screen_width() - frame_thickness
        height = gtk.gdk.screen_height() - frame_thickness

        return gtk.gdk.Rectangle(x, y, width, height)
