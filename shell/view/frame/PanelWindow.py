# Copyright (C) 2006, Red Hat, Inc.
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

import gtk
import hippo

from sugar.graphics import units
from sugar.graphics.window import Window

class PanelWindow(Window):
    def __init__(self, orientation):
        Window.__init__(self)
        self._orientation = orientation

        self.set_decorated(False)
        self.connect('realize', self._realize_cb)

        self._bg = hippo.CanvasBox(background_color=0x414141ff,
                                   orientation=self._orientation)
        self.set_root(self._bg)

        self._update_size()
    
        screen = gtk.gdk.screen_get_default()
        screen.connect('size-changed', self._size_changed_cb)

    def get_root(self):
        return self._bg
        
    def _update_size(self):
        padding = units.grid_to_pixels(1)
        if self._orientation == hippo.ORIENTATION_HORIZONTAL:
            self._bg.props.padding_left = padding
            self._bg.props.padding_right = padding
            self._bg.props.padding_top = 0
            self._bg.props.padding_bottom = 0

            width = gtk.gdk.screen_width()
            height = units.grid_to_pixels(1)
        else:
            self._bg.props.padding_left = 0
            self._bg.props.padding_right = 0
            self._bg.props.padding_top = padding
            self._bg.props.padding_bottom = padding

            width = units.grid_to_pixels(1)
            height = gtk.gdk.screen_height()
        self.resize(width, height)

    def _realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(False)
        
    def _size_changed_cb(self, screen):
        self._update_size()
