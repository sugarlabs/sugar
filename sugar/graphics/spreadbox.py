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

from array import array
from random import random

import gobject
import hippo

_X_TILES = 120
_NUM_TRIALS = 20
_MAX_WEIGHT = 255

class _Grid(object):
    def __init__(self, x_tiles, y_tiles, cell_size):
        self._array = array('B')
        self.x_tiles = x_tiles
        self.y_tiles = y_tiles
        self.cell_size = cell_size

        for i in range(self.y_tiles * self.x_tiles):
            self._array.append(0)
    
    def __getitem__(self, (row, col)):
        return self._array[col + row * self.x_tiles]

    def __setitem__(self, (row, col), value):
        self._array[col + row * self.x_tiles] = value

    def compute_weight_at(self, x, y, width, height):
        weight = 0

        for i in range(x, x + width):
            for j in range(y, y + height):
                weight += self[j, i]
                
        return weight

    def add_weight_at(self, x, y, width, height):
        for i in range(x, x + width):
            for j in range(y, y + height):
                self[j, i] += 1

    def remove_weight_at(self, x, y, width, height):
        for i in range(x, x + width):
            for j in range(y, y + height):
                self[j, i] -= 1
                
    def from_canvas(self, dim):
        return dim / self.cell_size

    def to_canvas(self, dim):
        return dim * self.cell_size

class _ItemInfo(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)
        self.x = -1
        self.y = -1
        self.width = -1
        self.height = -1
        
    def add_weight(self, grid):
        grid.add_weight_at(self.x, self.y, self.width, self.height)

    def remove_weight(self, grid):
        grid.remove_weight_at(self.x, self.y, self.width, self.height)

    def compute_weight(self, grid, x=-1, y=-1):
        if x < 0:
            x = self.x
        if y < 0:
            y = self.y

        grid.compute_weight_at(x, y, self.width, self.height)

class SpreadBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarSpreadBox'
    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)

        self._grid = None
        self._center = None
        self._width = -1
        self._height = -1

    def set_center_item(self, item):
        if self._center:
            self.remove(self._center)

        self.append(item, hippo.PACK_FIXED)
        self._center = item

        self._layout_center()

    def add_item(self, item):
        item.set_data('item-info', _ItemInfo())
        self.append(item, hippo.PACK_FIXED)
        self._layout_item(item)

    def remove_item(self, item):
        info = item.get_data('item-info')
        info.remove_weigth(self._grid)
        
        self.remove(item)

    def _place_item(self, item, x, y):
        info = item.get_data('item-info')
        info.x = x
        info.y = y
        info.add_weight(self._grid)        

        self.set_position(item, self._grid.to_canvas(x),
                          self._grid.to_canvas(y))

    def _layout_item(self, item):
        if not self._grid:
            return

        info = item.get_data('item-info')

        [width, height] = item.get_allocation()
        info.width = self._grid.from_canvas(width)
        info.height = self._grid.from_canvas(height)

        trials = _NUM_TRIALS
        placed = False
        best_weight = _MAX_WEIGHT

        while trials > 0 and not placed:
            x = int(random() * (self._grid.x_tiles - info.width))
            y = int(random() * (self._grid.y_tiles - info.height))

            weight = info.compute_weight(self._grid, x, y)

            if weight == 0:
                self._place_item(item, x, y)
                placed = True
            elif weight < best_weight:
                best_x = x
                best_y = y

            trials -= 1
            
        if not placed:
            self._place_item(item, best_x, best_y)

    def _layout(self):        
        for item in self.get_children():
            if item != self._center:
                self._layout_item(item)

    def _layout_center(self):
        if not self._center or not self._grid:
            return
        
        [width, height] = self._center.get_allocation()
        x = (self._width - width) / 2
        y = (self._height - height) / 2        
        self.set_position(self._center, x, y)
                          
    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        if width != self._width or height != self._height:
            cell_size = width / _X_TILES
            y_tiles = height / cell_size
        
            self._grid = _Grid(_X_TILES, y_tiles, cell_size)
            self._width = width
            self._height = height

            self._layout()

        self._layout_center()
