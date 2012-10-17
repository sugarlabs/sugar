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

from gi.repository import Gtk

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
        # FIXME what is this for?
        self.set_realized(True)
        self.set_window(self.get_parent_window())
        self.style.attach(self.window)
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
        if not child in self._children:
            return

        if not self._children[child]:  # not centered
            self._nflakes -= 1

        del self._children[child]
        self.remove(child)

    def do_size_request(self, requisition):
        size = self._calculate_size()
        requisition.width = size
        requisition.height = size

    def do_size_allocate(self, allocation):
        r = self._get_radius()
        index = 0

        for child, centered in self._children.items():
            child_width, child_height = child.size_request()
            rect = (0, 0, child_width, child_height)

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
                child_w, child_h = child.size_request()
                radius += max(child_w, child_h) / 2

        return radius

    def _calculate_size(self):
        thickness = 0
        for child in self._children.keys():
            width, height = child.size_request()
            thickness = max(thickness, max(width, height))

        return self._get_radius() * 2 + thickness
