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

import math

import cairo
import hippo

from sugar.graphics import units

_BASE_RADIUS = units.points_to_pixels(20)
_CHILDREN_FACTOR = 1
_FLAKE_DISTANCE = units.points_to_pixels(4)

class SnowflakeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarSnowflakeBox'
    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self._root = None

    def set_root(self, icon):
        self._root = icon

    def _get_center(self):
        [width, height] = self.get_allocation()
        return [width / 2, height / 2]

    def _get_radius(self):
        return _BASE_RADIUS + _CHILDREN_FACTOR * self._get_n_children()

    def _layout_root(self):
        [width, height] = self._root.get_allocation()
        [cx, cy] = self._get_center()

        x = cx - (width / 2)
        y = cy - (height / 2)

        self.set_position(self._root, int(x), int(y))

    def _get_n_children(self):
        return len(self.get_children()) - 1

    def _layout_child(self, child, index):
        r = self._get_radius()
        if (self._get_n_children() > 10):
            r += _FLAKE_DISTANCE * (index % 3)

        angle = 2 * math.pi * index / self._get_n_children()

        [width, height] = child.get_allocation()
        [cx, cy] = self._get_center()

        x = cx + math.cos(angle) * r - (width / 2)
        y = cy + math.sin(angle) * r - (height / 2)

        self.set_position(child, int(x), int(y))

    def _calculate_size(self):
        max_child_size = 0
        
        for child in self.get_children():
            [min_w, natural_w] = child.get_width_request()
            [min_h, natural_h] = child.get_height_request(min_w)
            max_child_size = max (max_child_size, min_w)
            max_child_size = max (max_child_size, min_h)

        return self._get_radius() * 2 + max_child_size + _FLAKE_DISTANCE * 2

    def do_get_height_request(self, for_width):
        hippo.CanvasBox.do_get_height_request(self, for_width)
        
        size = self._calculate_size()
        
        return (size, size)

    def do_get_width_request(self):
        hippo.CanvasBox.do_get_width_request(self)

        size = self._calculate_size()
        
        return (size, size)

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        self._layout_root()

        index = 0
        for child in self.get_children():
            if child != self._root:
                self._layout_child(child, index)
                index += 1
