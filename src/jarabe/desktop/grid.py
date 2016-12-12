# Copyright (C) 2007 Red Hat, Inc.
# Copyright (C) 2008 One Laptop Per Child
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

import random

from gi.repository import GObject
from gi.repository import Gdk

from gi.repository import SugarExt


_PLACE_TRIALS = 20
_MAX_WEIGHT = 255
_REFRESH_RATE = 200
_MAX_COLLISIONS_PER_REFRESH = 20


class Grid(SugarExt.Grid):
    __gsignals__ = {
        'child-changed': (GObject.SignalFlags.RUN_FIRST, None,
                          ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self, width, height):
        GObject.GObject.__init__(self)

        self._children = []
        self._child_rects = {}
        self._locked_children = set()
        self._collisions = []
        self._collisions_sid = 0

        self.setup(width, height)

    def add(self, child, width, height, x=None, y=None, locked=False):
        if x is not None and y is not None:
            rect = Gdk.Rectangle()
            rect.x = x
            rect.y = y
            rect.width = width
            rect.height = height
            weight = self.compute_weight(rect)
        else:
            trials = _PLACE_TRIALS
            weight = _MAX_WEIGHT
            while trials > 0 and weight:
                rect = Gdk.Rectangle()
                rect.x = int(random.random() * (self.width - width))
                rect.y = int(random.random() * (self.height - height))
                rect.width = width
                rect.height = height
                new_weight = self.compute_weight(rect)
                if weight > new_weight:
                    weight = new_weight

                trials -= 1

        self._child_rects[child] = rect
        self._children.append(child)
        self.add_weight(self._child_rects[child])
        if locked:
            self._locked_children.add(child)

        if weight > 0:
            self._detect_collisions(child)

    def is_in_grid(self, child):
        return child in self._children

    def remove(self, child):
        self._children.remove(child)
        self.remove_weight(self._child_rects[child])
        self._locked_children.discard(child)
        del self._child_rects[child]

        if child in self._collisions:
            self._collisions.remove(child)

    def move(self, child, x, y, locked=False):
        self.remove_weight(self._child_rects[child])

        rect = self._child_rects[child]
        rect.x = x
        rect.y = y

        weight = self.compute_weight(rect)
        self.add_weight(self._child_rects[child])

        if locked:
            self._locked_children.add(child)
        else:
            self._locked_children.discard(child)

        if weight > 0:
            self._detect_collisions(child)

    def _shift_child(self, child, weight):
        rect = self._child_rects[child]

        new_rects = []

        def _create_rectangle(x, y, width, height):
            rect = Gdk.Rectangle()
            rect.x, rect.y = x, y
            rect.width, rect.height = width, height
            return rect

        # Get rects right, left, bottom and top
        if (rect.x + rect.width < self.width - 1):
            new_rects.append(_create_rectangle(rect.x + 1, rect.y,
                                               rect.width, rect.height))

        if (rect.x - 1 > 0):
            new_rects.append(_create_rectangle(rect.x - 1, rect.y,
                                               rect.width, rect.height))

        if (rect.y + rect.height < self.height - 1):
            new_rects.append(_create_rectangle(rect.x, rect.y + 1,
                                               rect.width, rect.height))

        if (rect.y - 1 > 0):
            new_rects.append(_create_rectangle(rect.x, rect.y - 1,
                                               rect.width, rect.height))

        # Get diagonal rects
        if rect.x + rect.width < self.width - 1 and \
                rect.y + rect.height < self.height - 1:
            new_rects.append(_create_rectangle(rect.x + 1, rect.y + 1,
                                               rect.width, rect.height))

        if rect.x - 1 > 0 and rect.y + rect.height < self.height - 1:
            new_rects.append(_create_rectangle(rect.x - 1, rect.y + 1,
                                               rect.width, rect.height))

        if rect.x + rect.width < self.width - 1 and rect.y - 1 > 0:
            new_rects.append(_create_rectangle(rect.x + 1, rect.y - 1,
                                               rect.width, rect.height))

        if rect.x - 1 > 0 and rect.y - 1 > 0:
            new_rects.append(_create_rectangle(rect.x - 1, rect.y - 1,
                                               rect.width, rect.height))

        random.shuffle(new_rects)

        best_rect = None
        for new_rect in new_rects:
            new_weight = self.compute_weight(new_rect)
            if new_weight < weight:
                best_rect = new_rect
                weight = new_weight

        if best_rect:
            self._child_rects[child] = best_rect
            weight = self._shift_child(child, weight)

        return weight

    def __solve_collisions_cb(self):
        for i_ in range(_MAX_COLLISIONS_PER_REFRESH):
            collision = self._collisions.pop(0)

            old_rect = self._child_rects[collision]
            self.remove_weight(old_rect)
            weight = self.compute_weight(old_rect)
            weight = self._shift_child(collision, weight)
            self.add_weight(self._child_rects[collision])

            # TODO: we shouldn't give up the first time we failed to find a
            # better position.
            if old_rect != self._child_rects[collision]:
                self._detect_collisions(collision)
                self.emit('child-changed', collision)
                if weight > 0:
                    self._collisions.append(collision)

            if not self._collisions:
                self._collisions_sid = 0
                return False

        return True

    def _detect_collisions(self, child):
        collision_found = False
        child_rect = self._child_rects[child]
        for c in self._children:
            intersects_, intersection = Gdk.rectangle_intersect(
                child_rect, self._child_rects[c])
            if c != child and intersection.width > 0:
                collision_found = True
                if (c not in self._locked_children and
                        c not in self._collisions):
                    self._collisions.append(c)

        if collision_found:
            if child not in self._collisions:
                self._collisions.append(child)

        if self._collisions and not self._collisions_sid:
            self._collisions_sid = \
                GObject.timeout_add(_REFRESH_RATE,
                                    self.__solve_collisions_cb,
                                    priority=GObject.PRIORITY_LOW)

    def get_child_rect(self, child):
        return self._child_rects[child]
