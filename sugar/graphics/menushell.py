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

	def __init__(self):
		gobject.GObject.__init__(self)
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
