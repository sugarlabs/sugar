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

class MenuShell(gobject.GObject):
	__gsignals__ = {
		'activated':   (gobject.SIGNAL_RUN_FIRST,
				        gobject.TYPE_NONE, ([])),
		'deactivated': (gobject.SIGNAL_RUN_FIRST,
				        gobject.TYPE_NONE, ([])),
	}

	def __init__(self, parent_canvas):
		gobject.GObject.__init__(self)

		self._parent_canvas = parent_canvas
		self._menu_controller = None

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

	def _get_item_origin(self, item):
		[x, y] = item.get_context().translate_to_widget(item)

		[origin_x, origin_y] = self._parent_canvas.window.get_origin()
		x += origin_x
		y += origin_y

		return [x, y]

	def get_position(self, menu, item):
		[x, y] = self._get_item_origin(item)
		[width, height] = item.get_allocation()

		[canvas_x, canvas_y] = self._parent_canvas.window.get_origin()
		canvas_rect = self._parent_canvas.get_allocation()
		[menu_w, menu_h] = menu.size_request()

		menu_x = x
		menu_y = y + height

		if (menu_x + menu_w > canvas_x) and \
		   (menu_y < canvas_y + canvas_rect.height):
			menu_x = x - menu_w
			menu_y = y

		return [menu_x, menu_y]
