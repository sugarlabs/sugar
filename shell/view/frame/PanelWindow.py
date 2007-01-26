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

from sugar.graphics.menushell import MenuShell

class PanelWindow(gtk.Window):
    def __init__(self, width, height):
        gtk.Window.__init__(self)

        self.set_decorated(False)
        self.connect('realize', self._realize_cb)

        canvas = hippo.Canvas()

        self._bg = hippo.CanvasBox(background_color=0x414141ff)
        canvas.set_root(self._bg)

        self.add(canvas)
        canvas.show()

        self._menu_shell = MenuShell(canvas)

        self.resize(width, height)

    def get_menu_shell(self):
        return self._menu_shell

    def get_root(self):
        return self._bg

    def _realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(False)
