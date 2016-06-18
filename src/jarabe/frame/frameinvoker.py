# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gdk

from sugar3.graphics import style
from sugar3.graphics.palette import WidgetInvoker


def _get_screen_area():
    frame_thickness = style.GRID_CELL_SIZE

    screen_area = Gdk.Rectangle()
    screen_area.x = screen_area.y = frame_thickness
    screen_area.width = Gdk.Screen.width() - frame_thickness
    screen_area.height = Gdk.Screen.height() - frame_thickness

    return screen_area


class FrameWidgetInvoker(WidgetInvoker):

    def __init__(self, widget):
        WidgetInvoker.__init__(self, widget, widget.get_child())

        self._position_hint = self.ANCHORED
        self._screen_area = _get_screen_area()
