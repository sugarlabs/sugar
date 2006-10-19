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

import gobject
import gtk
import logging

from _sugar import Browser
from _sugar import PushScroller

class _PopupCreator(gobject.GObject):
	__gsignals__ = {
		'popup-created':  (gobject.SIGNAL_RUN_FIRST,
						   gobject.TYPE_NONE, ([])),
	}

	def __init__(self, parent_window):
		gobject.GObject.__init__(self)

		logging.debug('Creating the popup widget')

		self._sized_popup = False
		self._parent_window = parent_window

		self._dialog = gtk.Window()
		self._dialog.set_resizable(True)

		self._dialog.realize()
		self._dialog.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

		self._embed = Browser()
		self._size_to_sid = self._embed.connect('size_to', self._size_to_cb)
		self._vis_sid = self._embed.connect('visibility', self._visibility_cb)

		self._dialog.add(self._embed)

	def _size_to_cb(self, embed, width, height):
		logging.debug('Resize the popup to %d %d' % (width, height))
		self._sized_popup = True
		self._dialog.resize(width, height)

	def _visibility_cb(self, embed, visible):
		if visible:
			if self._sized_popup:
				logging.debug('Show the popup')
				self._embed.show()
				self._dialog.set_transient_for(self._parent_window)
				self._dialog.show()
			else:
				logging.debug('Open a new activity for the popup')
				self._dialog.remove(self._embed)

				activity = BrowserActivity(self._embed)
				activity.set_type('com.redhat.Sugar.BrowserActivity')

			self._embed.disconnect(self._size_to_sid)
			self._embed.disconnect(self._vis_sid)

			self.emit('popup-created')

	def get_embed(self):
		return self._embed

class WebBrowser(Browser):
	__gtype_name__ = "SugarWebBrowser"

	def __init__(self):
		Browser.__init__(self)
		self._popup_creators = []

	def do_create_window(self):
		popup_creator = _PopupCreator(self.get_toplevel())
		popup_creator.connect('popup-created', self._popup_created_cb)

		self._popup_creators.append(popup_creator)

		return popup_creator.get_embed()

	def _popup_created_cb(self, creator):
		self._popup_creators.remove(creator)
