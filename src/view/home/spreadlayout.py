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

import hippo
import gobject
import gtk

from sugar.graphics import style

from view.home.grid import Grid

_CELL_SIZE = 4

class SpreadLayout(gobject.GObject, hippo.CanvasLayout):
    __gtype_name__ = 'SugarSpreadLayout'
    def __init__(self):
        gobject.GObject.__init__(self)
        self._box = None

        min_width, width = self.do_get_width_request()
        min_height, height = self.do_get_height_request(width)

        self._grid = Grid(width / _CELL_SIZE, height / _CELL_SIZE)
        self._grid.connect('child-changed', self._grid_child_changed_cb)

    def add(self, child):
        self._box.append(child)

        width, height = self._get_child_grid_size(child)
        self._grid.add(child, width, height)

    def remove(self, child):
        self._grid.remove(child)
        self._box.remove(child)

    def move(self, child, x, y):
        self._grid.move(child, x / _CELL_SIZE, y / _CELL_SIZE, locked=True)

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

            rect = self._grid.get_child_rect(child.item)
            child.allocate(rect.x * _CELL_SIZE,
                           rect.y * _CELL_SIZE,
                           rect.width * _CELL_SIZE,
                           rect.height * _CELL_SIZE,
                           origin_changed)

    def _get_child_grid_size(self, child):
        min_width, width = child.get_width_request()
        min_height, height = child.get_height_request(width)

        return int(width / _CELL_SIZE), int(height / _CELL_SIZE)

    def _grid_child_changed_cb(self, grid, child):
        child.emit_request_changed()

