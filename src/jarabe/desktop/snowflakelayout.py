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
import gi
gi.require_version('Gsk', '4.0')
gi.require_version('Graphene', '1.0')
from gi.repository import Gsk, Graphene

from sugar4.graphics import style

_BASE_DISTANCE = style.zoom(25)
_CHILDREN_FACTOR = style.zoom(3)


class SnowflakeLayout(Gtk.Widget):
    __gtype_name__ = 'SugarSnowflakeLayout'

    def __init__(self):
        super().__init__()
        self._nflakes = 0
        self._children = {}

    def do_dispose(self):
        for child in list(self._children.keys()):
            child.unparent()
        self._children.clear()
        self._nflakes = 0

    def add(self, child):
        child.set_parent(self)

    def remove(self, child):
        if child not in self._children:
            return

        if not self._children[child]:  # not centered
            self._nflakes -= 1

        del self._children[child]
        child.unparent()

    def add_icon(self, child, center=False):
        if not center:
            self._nflakes += 1

        self._children[child] = center
        self.add(child)

    def _child_size(self, child):
        _, nat_w, _, _ = child.measure(Gtk.Orientation.HORIZONTAL, -1)
        _, nat_h, _, _ = child.measure(Gtk.Orientation.VERTICAL, -1)
        return nat_w, nat_h

    def do_measure(self, orientation, for_size):
        size = self._calculate_size()
        return (size, size, -1, -1)

    def do_size_allocate(self, width, height, baseline):
        r = self._get_radius()
        index = 0

        for child, centered in list(self._children.items()):
            child_width, child_height = self._child_size(child)
            
            rect = Gdk.Rectangle()
            rect.width = child_width
            rect.height = child_height

            w = width - child_width
            h = height - child_height
            if centered:
                rect.x = w / 2
                rect.y = h / 2
            else:
                angle = 2 * math.pi * index / self._nflakes

                if self._nflakes != 2:
                    angle -= math.pi / 2

                dx = math.cos(angle) * r
                dy = math.sin(angle) * r

                rect.x = int(w / 2 + dx)
                rect.y = int(h / 2 + dy)

                index += 1

            transform = Gsk.Transform.new().translate(Graphene.Point().init(rect.x, rect.y))
            child.allocate(rect.width, rect.height, -1, transform)

    def _get_radius(self):
        radius = int(_BASE_DISTANCE + _CHILDREN_FACTOR * self._nflakes)
        for child, centered in list(self._children.items()):
            if centered:
                child_width, child_height = self._child_size(child)
                radius += max(child_width, child_height) / 2
        return radius

    def _calculate_size(self):
        thickness = 0
        for child in list(self._children.keys()):
            child_width, child_height = self._child_size(child)
            thickness = max(thickness, max(child_width, child_height))

        return self._get_radius() * 2 + thickness

    def do_snapshot(self, snapshot):
        for child in list(self._children.keys()):
            self.snapshot_child(child, snapshot)
