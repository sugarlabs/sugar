# Copyright (C) 2006-2007 Red Hat, Inc.
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

import math

from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics import style


_BASE_DISTANCE = style.zoom(25)
_CHILDREN_FACTOR = style.zoom(3)


class SnowflakeLayout(Gtk.Container):
    __gtype_name__ = 'SugarSnowflakeLayout'

    def __init__(self):
        Gtk.Container.__init__(self)
        self.set_has_window(False)
        self._nflakes = 0
        self._children = {}

    def do_realize(self):
        self.set_realized(True)
        self.set_window(self.get_parent_window())
        for child in self._children.keys():
            child.set_parent_window(self.get_parent_window())
        self.queue_resize()

    def do_add(self, child):
        if child.get_realized():
            child.set_parent_window(self.get_parent_window())
        child.set_parent(self)

    def do_forall(self, include_internals, callback):
        for child in self._children.keys():
            callback(child)

    def do_remove(self, child):
        child.unparent()

    def add_icon(self, child, center=False):
        if not center:
            self._nflakes += 1

        self._children[child] = center
        self.add(child)

    def remove(self, child):
        if child not in self._children:
            return

        if not self._children[child]:  # not centered
            self._nflakes -= 1

        del self._children[child]
        self.remove(child)

    def do_get_preferred_size(self):
        size = self._calculate_size()
        requisition = Gtk.Requisition()
        requisition.width = size
        requisition.height = size
        return (requisition, requisition)

    def do_get_preferred_width(self):
        size = self._calculate_size()
        return (size, size)

    def do_get_preferred_height(self):
        size = self._calculate_size()
        return (size, size)

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)

        r = self._get_radius()
        index = 0

        for child, centered in self._children.items():
            child_request = child.size_request()
            child_width, child_height = \
                child_request.width, child_request.height
            rect = Gdk.Rectangle()
            rect.x = 0
            rect.y = 0
            rect.width = child_width
            rect.height = child_height

            width = allocation.width - child_width
            height = allocation.height - child_height
            if centered:
                rect.x = allocation.x + width / 2
                rect.y = allocation.y + height / 2
            else:
                angle = 2 * math.pi * index / self._nflakes

                if self._nflakes != 2:
                    angle -= math.pi / 2

                dx = math.cos(angle) * r
                dy = math.sin(angle) * r

                rect.x = int(allocation.x + width / 2 + dx)
                rect.y = int(allocation.y + height / 2 + dy)

                index += 1

            child.size_allocate(rect)

    def _get_radius(self):
        radius = int(_BASE_DISTANCE + _CHILDREN_FACTOR * self._nflakes)
        for child, centered in self._children.items():
            if centered:
                child_request = child.size_request()
                child_width, child_height = \
                    child_request.width, child_request.height
                radius += max(child_width, child_height) / 2

        return radius

    def _calculate_size(self):
        thickness = 0
        for child in self._children.keys():
            child_request = child.size_request()
            child_width, child_height = \
                child_request.width, child_request.height
            thickness = max(thickness, max(child_width, child_height))

        return self._get_radius() * 2 + thickness
