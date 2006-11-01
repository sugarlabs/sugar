# vi: ts=4 ai noet
#
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

import logging
import gobject
import dbus
import dbus.service
from sugar import env

_CLIPBOARD_SERVICE = "org.laptop.Clipboard"
_CLIPBOARD_DBUS_INTERFACE = "org.laptop.Clipboard"
_CLIPBOARD_OBJECT_PATH = "/org/laptop/Clipboard"

class ClipboardDBusServiceHelper(dbus.service.Object):
	def __init__(self, parent):
		self._parent = parent

		bus = dbus.SessionBus()
		bus_name = dbus.service.BusName(_CLIPBOARD_DBUS_INTERFACE, bus=bus)
		dbus.service.Object.__init__(self, bus_name, _CLIPBOARD_OBJECT_PATH)
		
	@dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
						 in_signature="ss", out_signature="")
	def add_object(self, mimeType, fileName):
		logging.debug('Added object of type ' + mimeType + ' with path at ' + fileName)
		self.object_added(mimeType, fileName)

	@dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
						 in_signature="s", out_signature="")
	def delete_object(self, fileName):
		logging.debug('Deleted object with path at ' + fileName)
		self.object_deleted(fileName)

	@dbus.service.method(_CLIPBOARD_DBUS_INTERFACE,
						 in_signature="si", out_signature="")
	def update_object_state(self, fileName, percent):
		logging.debug('Updated object with path at ' + fileName + ' with percent ' + str(percent))
		self.object_state_updated(fileName, percent)

	@dbus.service.signal(_CLIPBOARD_DBUS_INTERFACE, signature="ss")
	def object_added(self, mimeType, fileName):
		pass

	@dbus.service.signal(_CLIPBOARD_DBUS_INTERFACE, signature="s")
	def object_deleted(self, fileName):
		pass

	@dbus.service.signal(_CLIPBOARD_DBUS_INTERFACE, signature="si")
	def object_state_updated(self, fileName, percent):
		pass

class ClipboardService(object):
	def __init__(self):
		self._dbus_helper = ClipboardDBusServiceHelper(self)

	def run(self):
		loop = gobject.MainLoop()
		try:
			loop.run()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
