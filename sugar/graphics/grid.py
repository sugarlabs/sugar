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

import gtk

COLS = 16
ROWS = 12

class Grid(object):
    def __init__(self):
        self._factor = gtk.gdk.screen_width() / COLS

    def point(self, grid_x, grid_y):
        return [grid_x * self._factor, grid_y * self._factor]

    def rectangle(self, grid_x, grid_y, grid_w, grid_h):
        return [grid_x * self._factor, grid_y * self._factor,
                grid_w * self._factor, grid_h * self._factor]

    def dimension(self, grid_dimension):
        return grid_dimension * self._factor

    def fit_point(self, x, y):
        return [int(x / self._factor), int(y / self._factor)]
    
