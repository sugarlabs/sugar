# Copyright (C) 2007 Red Hat, Inc.
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

from numpy import array
import random

import hippo
import gobject
import gtk

from sugar.graphics import style

_PLACE_TRIALS = 20
_MAX_WEIGHT = 255
_CELL_SIZE = 4
_REFRESH_RATE = 200
_MAX_COLLISIONS_PER_REFRESH = 20

class _Grid(gobject.GObject):
    __gsignals__ = {
        'child-changed' : (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([gobject.TYPE_PYOBJECT]))
    }
    def __init__(self, width, height):
        gobject.GObject.__init__(self)

        self.width = width
        self.height = height
        self._children = []
        self._collisions = []
        self._collisions_sid = 0

        self._array = array([0], dtype='b')
        self._array.resize(width * height)

    def add(self, child, width, height):
        trials = _PLACE_TRIALS
        weight = _MAX_WEIGHT
        while trials > 0 and weight:
            x = int(random.random() * (self.width - width))
            y = int(random.random() * (self.height - height))

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
        self.add_weight(child.grid_rect)

    def _shift_child(self, child, weight):
        rect = child.grid_rect
        
        new_rects = []

        if (rect.x + rect.width < self.width - 1):
            new_rects.append(gtk.gdk.Rectangle(rect.x + 1, rect.y,
                                               rect.width, rect.height))

        if (rect.x - 1 > 0):
            new_rects.append(gtk.gdk.Rectangle(rect.x - 1, rect.y,
                                               rect.width, rect.height))

        if (rect.y + rect.height < self.height - 1):
            new_rects.append(gtk.gdk.Rectangle(rect.x, rect.y + 1,
                                               rect.width, rect.height))

        if (rect.y - 1 > 0):
            new_rects.append(gtk.gdk.Rectangle(rect.x, rect.y - 1,
                                               rect.width, rect.height))

        if rect.x + rect.width < self.width - 1 and \
                rect.y + rect.height < self.height - 1:
            new_rects.append(gtk.gdk.Rectangle(rect.x + 1, rect.y + 1,
                                               rect.width, rect.height))

        if rect.x - 1 > 0 and rect.y + rect.height < self.height - 1:
            new_rects.append(gtk.gdk.Rectangle(rect.x - 1, rect.y + 1,
                                               rect.width, rect.height))

        if rect.x + rect.width < self.width - 1 and rect.y - 1 > 0:
            new_rects.append(gtk.gdk.Rectangle(rect.x + 1, rect.y - 1,
                                               rect.width, rect.height))

        if rect.x - 1 > 0 and rect.y - 1 > 0:
            new_rects.append(gtk.gdk.Rectangle(rect.x - 1, rect.y - 1,
                                               rect.width, rect.height))

        random.shuffle(new_rects)

        best_rect = None
        for new_rect in new_rects:
            new_weight = self._compute_weight(new_rect)
            if new_weight < weight:
                best_rect = new_rect
                weight = new_weight
        
        if best_rect:
            child.grid_rect = best_rect
            weight = self._shift_child(child, weight)

        return weight

    def __solve_collisions_cb(self):
        for i in range(_MAX_COLLISIONS_PER_REFRESH):
            collision = self._collisions.pop(0)

            old_rect = collision.grid_rect
            self._remove_weight(collision.grid_rect)
            weight = self._compute_weight(collision.grid_rect)
            weight = self._shift_child(collision, weight)
            self.add_weight(collision.grid_rect)

            # TODO: we shouldn't give up the first time we failed to find a
            # better position.
            if old_rect != collision.grid_rect:
                self._detect_collisions(collision)
                self.emit('child-changed', collision)
                if weight > 0:
                    self._collisions.append(collision)

            if not self._collisions:
                return False

        return True

    def _detect_collisions(self, child):
        collision_found = False
        for c in self._children:
            intersection = child.grid_rect.intersect(c.grid_rect)
            if c != child and intersection.width > 0:
                if c not in self._collisions:
                    collision_found = True
                    self._collisions.append(c)

        if collision_found:
            if child not in self._collisions:
                self._collisions.append(child)

        if len(self._collisions) and not self._collisions_sid:
            self._collisions_sid = gobject.timeout_add(_REFRESH_RATE,
                    self.__solve_collisions_cb, priority=gobject.PRIORITY_LOW)

    def add_weight(self, rect):
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


class SpreadLayout(gobject.GObject, hippo.CanvasLayout):
    __gtype_name__ = 'SugarSpreadLayout'
    def __init__(self):
        gobject.GObject.__init__(self)
        self._box = None

        min_width, width = self.do_get_width_request()
        min_height, height = self.do_get_height_request(width)

        self._grid = _Grid(width / _CELL_SIZE, height / _CELL_SIZE)
        self._grid.connect('child-changed', self._grid_child_changed_cb)

    def add_center(self, child, vertical_offset=0):
        self._box.append(child)

        width, height = self._get_child_grid_size(child)
        rect = gtk.gdk.Rectangle(int((self._grid.width - width) / 2),
                                 int((self._grid.height - height) / 2),
                                 width + 1, height + 1)
        self._grid.add_weight(rect)

        box_child = self._box.find_box_child(child)
        box_child.grid_rect = None
        box_child.vertical_offset = vertical_offset

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
        return 0, gtk.gdk.screen_height() - style.GRID_CELL_SIZE

    def do_get_width_request(self):
        return 0, gtk.gdk.screen_width()

    def do_allocate(self, x, y, width, height,
                    req_width, req_height, origin_changed):
        for child in self._box.get_layout_children():
            # We need to always get  requests to not confuse hippo
            min_w, child_width = child.get_width_request()
            min_h, child_height = child.get_height_request(child_width)

            rect = child.grid_rect
            if child.grid_rect:
                child.allocate(rect.x * _CELL_SIZE,
                               rect.y * _CELL_SIZE,
                               rect.width * _CELL_SIZE,
                               rect.height * _CELL_SIZE,
                               origin_changed)
            else:
                vertical_offset = child.vertical_offset
                child_x = x + (width - child_width) / 2
                child_y = y + (height - child_height + vertical_offset) / 2
                child.allocate(child_x, child_y, child_width, child_height,
                               origin_changed)

    def _get_child_grid_size(self, child):
        min_width, width = child.get_width_request()
        min_height, height = child.get_height_request(width)

        return int(width / _CELL_SIZE), int(height / _CELL_SIZE)

    def _grid_child_changed_cb(self, grid, box_child):
        box_child.item.emit_request_changed()
