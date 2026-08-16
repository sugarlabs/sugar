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

from sugar4.graphics import style
from sugar4.graphics.palette import WidgetInvoker


def _get_screen_area():
    frame_thickness = style.GRID_CELL_SIZE

    display = Gdk.Display.get_default()
    width = 1024
    height = 768
    if display:
        monitors = display.get_monitors()
        if monitors and monitors.get_n_items() > 0:
            max_x, max_y = 0, 0
            for i in range(monitors.get_n_items()):
                geometry = monitors.get_item(i).get_geometry()
                max_x = max(max_x, geometry.x + geometry.width)
                max_y = max(max_y, geometry.y + geometry.height)
            width = max_x
            height = max_y

    screen_area = Gdk.Rectangle()
    screen_area.x = screen_area.y = frame_thickness
    screen_area.width = width - frame_thickness
    screen_area.height = height - frame_thickness

    return screen_area


class FrameWidgetInvoker(WidgetInvoker):

    def __init__(self, widget):
        WidgetInvoker.__init__(self, widget, widget)
        self._position_hint = self.ANCHORED
        self._screen_area = _get_screen_area()
