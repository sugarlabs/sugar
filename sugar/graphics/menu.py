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

import gtk
import hippo
import gobject

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics import style

class Menu(gtk.Window):
	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([int])),
	}

	def __init__(self, title=None, content_box=None):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		canvas = hippo.Canvas()
		self.add(canvas)
		canvas.show()

		self._root = hippo.CanvasBox()
		style.apply_stylesheet(self._root, 'menu')
		canvas.set_root(self._root)

		if title:
			self._title_item = hippo.CanvasText(text=title)
			style.apply_stylesheet(self._title_item, 'menu.Title')
			self._root.append(self._title_item)
		else:
			self._title_item = None

		if content_box:
			separator = self._create_separator()
			self._root.append(separator)
			self._root.append(content_box)

		self._action_box = None
		self._item_box = None

	def _create_separator(self):
		separator = hippo.CanvasBox()
		style.apply_stylesheet(separator, 'menu.Separator')
		return separator

	def _create_item_box(self):
		if self._title_item:
			separator = self._create_separator()
			self._root.append(separator)

		self._item_box = hippo.CanvasBox(
						orientation=hippo.ORIENTATION_VERTICAL)
		self._root.append(self._item_box)

	def _create_action_box(self):
		separator = self._create_separator()
		self._root.append(separator)

		self._action_box = hippo.CanvasBox(
						orientation=hippo.ORIENTATION_HORIZONTAL)
		self._root.append(self._action_box)

	def add_item(self, label, action_id):
		if not self._item_box:
			self._create_item_box()

		text = hippo.CanvasText(text=label)
		style.apply_stylesheet(text, 'menu.Item')

		# FIXME need a way to make hippo items activable in python
		text.connect('button-press-event', self._item_clicked_cb, action_id)
		#text.connect('activated', self._action_clicked_cb, action_id)

		self._item_box.append(text)

	def add_action(self, icon, action_id):
		if not self._action_box:
			self._create_action_box()

		style.apply_stylesheet(icon, 'menu.ActionIcon')
		icon.connect('activated', self._action_clicked_cb, action_id)
		self._action_box.append(icon)

	def _item_clicked_cb(self, icon, event, action):
		self.emit('action', action)

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)
