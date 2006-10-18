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

import hippo
import gobject
import logging

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.timeline import Timeline

class MenuIcon(CanvasIcon):
	def __init__(self, menu_shell, **kwargs):
		CanvasIcon.__init__(self, **kwargs)

		self._menu_shell = menu_shell
		self._menu = None
		self._hover_menu = False

		self._timeline = Timeline(self)
		self._timeline.add_tag('popup', 6, 6)
		self._timeline.add_tag('before_popdown', 7, 7)
		self._timeline.add_tag('popdown', 8, 8)

		self.connect('motion-notify-event', self._motion_notify_event_cb)

	def do_popup(self, current, n_frames):
		if self._menu:
			return

		self._menu = self.create_menu()

		self._menu.connect('enter-notify-event',
						   self._menu_enter_notify_event_cb)
		self._menu.connect('leave-notify-event',
						   self._menu_leave_notify_event_cb)

		[x, y] = self._menu_shell.get_position(self._menu, self)

		self._menu.move(x, y)
		self._menu.show()

		self._menu_shell.set_active(self)

	def do_popdown(self, current, frame):
		if self._menu:
			self._menu.destroy()
			self._menu = None
			self._menu_shell.set_active(None)

	def popdown(self):
		self._timeline.play('popdown', 'popdown')

	def _motion_notify_event_cb(self, item, event):
		if event.detail == hippo.MOTION_DETAIL_ENTER:
			self._timeline.play(None, 'popup')
		elif event.detail == hippo.MOTION_DETAIL_LEAVE:
			if not self._hover_menu:
				self._timeline.play('before_popdown', 'popdown')

	def _menu_enter_notify_event_cb(self, widget, event):
		self._hover_menu = True
		self._timeline.play('popup', 'popup')

	def _menu_leave_notify_event_cb(self, widget, event):
		self._hover_menu = False
		self._timeline.play('popdown', 'popdown')
