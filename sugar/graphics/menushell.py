# Copyright (C) 2006, Red Hat, Inc.
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

import gobject
import gtk

class MenuShell(gobject.GObject):
	__gsignals__ = {
		'activated':   (gobject.SIGNAL_RUN_FIRST,
				        gobject.TYPE_NONE, ([])),
		'deactivated': (gobject.SIGNAL_RUN_FIRST,
				        gobject.TYPE_NONE, ([])),
	}

	AUTO = 0
	LEFT = 1
	RIGHT = 2
	TOP = 3
	BOTTOM = 4

	def __init__(self, parent_canvas):
		gobject.GObject.__init__(self)

		self._parent_canvas = parent_canvas
		self._menu_controller = None
		self._position = MenuShell.AUTO

	def set_position(self, position):
		self._position = position

	def is_active(self):
		return (self._menu_controller != None)

	def set_active(self, controller):
		if controller == None:
			self.emit('deactivated')
		else:
			self.emit('activated')

		if self._menu_controller:
			self._menu_controller.popdown()
		self._menu_controller = controller

	def _get_item_rect(self, item):
		[x, y] = item.get_context().translate_to_widget(item)

		[origin_x, origin_y] = self._parent_canvas.window.get_origin()
		x += origin_x
		y += origin_y

		[w, h] = item.get_allocation()

		return [x, y, w, h]

	def get_position(self, menu, item):
		[item_x, item_y, item_w, item_h] = self._get_item_rect(item)
		[menu_w, menu_h] = menu.size_request()

		left_x = item_x - menu_w
		left_y = item_y
		right_x = item_x + item_w
		right_y = item_y
		top_x = item_x
		top_y = item_y - menu_h
		bottom_x = item_x
		bottom_y = item_y + item_h

		if self._position == MenuShell.LEFT:
			[x, y] = [left_x, left_y]
		elif self._position == MenuShell.RIGHT:
			[x, y] = [right_x, right_y]
		elif self._position == MenuShell.TOP:
			[x, y] = [top_x, top_y]
		elif self._position == MenuShell.BOTTOM:
			[x, y] = [bottom_x, bottom_y]
		elif self._position == MenuShell.AUTO:
			[x, y] = [right_x, right_y]
			if x + menu_w > gtk.gdk.screen_width():
				[x, y] = [left_x, left_y]

		x = min(x, gtk.gdk.screen_width())
		x = max(0, x)

		y = min(y, gtk.gdk.screen_height())
		y = max(0, y)

		return [x, y]
