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

import random

import hippo
import gtk

from sugar.graphics import units

_CELL_WIDTH  = units.grid_to_pixels(1)
_CELL_HEIGHT = units.grid_to_pixels(1)
_GRID_WIDTH  = gtk.gdk.screen_width() / _CELL_WIDTH
_GRID_HEIGHT = gtk.gdk.screen_height() / _CELL_HEIGHT

class SpreadBox(hippo.CanvasBox):
    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        self._grid = []

        for i in range(0, _GRID_WIDTH * _GRID_HEIGHT):
            self._grid.append(None)

    def add_item(self, item):
        start_pos = int(random.random() * len(self._grid))

        pos = start_pos
        while self._grid[pos] != None:
            pos = pos + 1
            if pos == len(self._grid):
                pos = 0
            elif pos == start_pos:
                break

        self._grid[pos] = item

        self.append(item, hippo.PACK_FIXED)

        cell_y = int(pos / _GRID_WIDTH)
        cell_x = pos - cell_y * _GRID_WIDTH
        self.set_position(item, cell_x * _CELL_WIDTH, cell_y * _CELL_HEIGHT)

    def remove_item(self, item):
        for i in range(0, len(self._grid)):
            if self._grid[i] == item:
                self._grid[i] = None
        self.remove(item)
