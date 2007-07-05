# Copyright (C) 2007 Red Hat, Inc.
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

import hippo
import gobject
import gtk

_PLACE_TRIALS = 20
_MAX_WEIGHT = 255
_CELL_SIZE = 4

class _Grid(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self._children = []
        self._collisions = []
        self._collisions_sid = 0

        self._array = array('B')
        for i in range(width * height):
            self._array.append(0)

    def add_locked(self, child, x, y, width, height):
        child.grid_rect = gtk.gdk.Rectangle(x, y, width, height)
        child.locked = True
        self._add_child(child)

    def add(self, child, width, height):
        trials = _PLACE_TRIALS
        weight = _MAX_WEIGHT
        while trials > 0 and weight:
            x = int(random() * (self.width - width))
            y = int(random() * (self.height - height))

            rect = gtk.gdk.Rectangle(x, y, width, height)
            new_weight = self._compute_weight(rect)
            if weight > new_weight:
                weight = new_weight

            trials -= 1

        child.grid_rect = rect
        child.locked = False

        self._add_child(child)

        if weight > 0:
            self._detect_collisions(child)

    def remove(self, child):
        self._children.remove(child)
        self._remove_weight(child.grid_rect)
        child.grid_rect = None

    def _add_child(self, child):
        self._children.append(child)
        self._add_weight(child.grid_rect)

    def _solve_collisions(self):
        return False

    def _detect_collisions(self, child):
        for c in self._children:
            intersection = child.grid_rect.intersect(c.grid_rect)
            if c != child and intersection.width > 0:
                if c not in self._collisions:
                    self._collisions.append(c)
                    if not self._collisions_sid:
                        self._collisions_sid = \
                            gobject.idle_add(self._solve_collisions)

    def _add_weight(self, rect):
        for i in range(rect.x, rect.x + rect.width):
            for j in range(rect.y, rect.y + rect.height):
                self[j, i] += 1

    def _remove_weight(self, rect):
        for i in range(rect.x, rect.x + rect.width):
            for j in range(rect.y, rect.y + rect.height):
                self[j, i] -= 1

    def _compute_weight(self, rect):
        weight = 0

        for i in range(rect.x, rect.x + rect.width):
            for j in range(rect.y, rect.y + rect.height):
                weight += self[j, i]
                
        return weight
    
    def __getitem__(self, (row, col)):
        return self._array[col + row * self.width]

    def __setitem__(self, (row, col), value):
        self._array[col + row * self.width] = value


class SpreadLayout(gobject.GObject,hippo.CanvasLayout):
    __gtype_name__ = 'SugarSpreadLayout'
    def __init__(self):
        gobject.GObject.__init__(self)

        min_width, width = self.do_get_width_request()
        min_height, height = self.do_get_height_request(width)

        self._grid = _Grid(width / _CELL_SIZE, height / _CELL_SIZE)

    def add_center(self, child):
        self._box.append(child)

        width, height = self._get_child_grid_size(child)
        box_child = self._box.find_box_child(child)
        self._grid.add_locked(box_child,
                              int((self._grid.width - width) / 2),
                              int((self._grid.height - height) / 2),
                              width, height)

    def add(self, child):
        self._box.append(child)

        width, height = self._get_child_grid_size(child)
        box_child = self._box.find_box_child(child)
        self._grid.add(box_child, width, height)

    def remove(self, child):
        box_child = self._box.find_box_child(child)
        self._grid.remove(box_child)

        self._box.remove(child)

    def do_set_box(self, box):
        self._box = box

    def do_get_height_request(self, for_width):
        return 0, gtk.gdk.screen_height()

    def do_get_width_request(self):
        return 0, gtk.gdk.screen_width()

    def do_allocate(self, x, y, width, height,
                    req_width, req_height, origin_changed):
        for child in self._box.get_layout_children():
            rect = child.grid_rect
            child.allocate(rect.x * _CELL_SIZE,
                           rect.y * _CELL_SIZE,
                           rect.width * _CELL_SIZE,
                           rect.height * _CELL_SIZE,
                           origin_changed)

    def _get_child_grid_size(self, child):
        min_width, width = child.get_width_request()
        min_height, height = child.get_height_request(width)

        return int(width / _CELL_SIZE), int(height / _CELL_SIZE)
