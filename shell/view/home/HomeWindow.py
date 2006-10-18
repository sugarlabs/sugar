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
import cairo

from sugar.graphics.menushell import MenuShell
import sugar
from view.home.MeshBox import MeshBox
from view.home.HomeBox import HomeBox
from view.home.FriendsBox import FriendsBox

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell

		self.set_default_size(gtk.gdk.screen_width(),
							  gtk.gdk.screen_height())

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

		self._nb = gtk.Notebook()
		self._nb.set_show_border(False)
		self._nb.set_show_tabs(False)

		self.add(self._nb)
		self._nb.show()

		canvas = hippo.Canvas()
		box = HomeBox(shell)
		canvas.set_root(box)
		self._nb.append_page(canvas)
		canvas.show()

		canvas = hippo.Canvas()
		box = FriendsBox(shell, MenuShell(canvas))
		canvas.set_root(box)
		self._nb.append_page(canvas)
		canvas.show()

		canvas = hippo.Canvas()
		box = MeshBox(shell, MenuShell(canvas))
		canvas.set_root(box)
		self._nb.append_page(canvas)
		canvas.show()

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_HOME:
			self._nb.set_current_page(0)
		elif level == sugar.ZOOM_FRIENDS:
			self._nb.set_current_page(1)
		elif level == sugar.ZOOM_MESH:
			self._nb.set_current_page(2)
