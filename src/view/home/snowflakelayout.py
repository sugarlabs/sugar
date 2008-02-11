# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import math

import gobject
import hippo

from sugar.graphics import style

_BASE_DISTANCE = style.zoom(15)
_CHILDREN_FACTOR = style.zoom(3)

class SnowflakeLayout(gobject.GObject,hippo.CanvasLayout):
    __gtype_name__ = 'SugarSnowflakeLayout'
    def __init__(self):
        gobject.GObject.__init__(self)
        self._nflakes = 0

    def add(self, child, center=False):
        if not center:
            self._nflakes += 1

        self._box.append(child)

        box_child = self._box.find_box_child(child)
        box_child.is_center = center

    def remove(self, child):
        box_child = self._box.find_box_child(child)
        if not box_child.is_center:
            self._nflakes -= 1

        self._box.remove(child)

    def do_set_box(self, box):
        self._box = box

    def do_get_height_request(self, for_width):
        size = self._calculate_size()
        return (size, size)

    def do_get_width_request(self):
        size = self._calculate_size()
        return (size, size)

    def do_allocate(self, x, y, width, height,
                    req_width, req_height, origin_changed):
        r = self._get_radius()
        index = 0

        for child in self._box.get_layout_children():
            cx = x + width / 2
            cy = x + height / 2

            min_width, child_width = child.get_width_request()
            min_height, child_height = child.get_height_request(child_width)

            if child.is_center:
                child.allocate(x + (width - child_width) / 2,
                               y + (height - child_height) / 2,
                               child_width, child_height, origin_changed)
            else:
                angle = 2 * math.pi * index / self._nflakes

                dx = math.cos(angle) * r
                dy = math.sin(angle) * r

                child_x = int(x + (width - child_width) / 2 + dx)
                child_y = int(y + (height - child_height) / 2 + dy)

                child.allocate(child_x, child_y, child_width,
                               child_height, origin_changed)

                index += 1

    def _get_radius(self):
        radius = int(_BASE_DISTANCE + _CHILDREN_FACTOR * self._nflakes)
        for child in self._box.get_layout_children():
            if child.is_center:
                [min_w, child_w] = child.get_width_request()
                [min_h, child_h] = child.get_height_request(child_w)
                radius += max(child_w, child_h) / 2

        return radius

    def _calculate_size(self):
        thickness = 0
        for child in self._box.get_layout_children():
            [min_width, child_width] = child.get_width_request()
            [min_height, child_height] = child.get_height_request(child_width)
            thickness = max(thickness, max(child_width, child_height))

        return self._get_radius() * 2 + thickness
