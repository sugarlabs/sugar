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

import dbus

DCON_MANAGER_INTERFACE = 'org.laptop.DCONManager'
DCON_MANAGER_SERVICE = 'org.laptop.DCONManager'
DCON_MANAGER_OBJECT_PATH = '/org/laptop/DCONManager'

class DCONManager(object):
	COLOR_MODE = 0
	BLACK_AND_WHITE_MODE = 1

	def __init__(self):
		bus = dbus.SystemBus()
		proxy = bus.get_object(DCON_MANAGER_SERVICE, DCON_MANAGER_OBJECT_PATH)
		self._service = dbus.Interface(proxy, DCON_MANAGER_INTERFACE)

	def set_mode(self, mode):
		self._service.set_mode(mode)

	def increase_brightness(self):
		level = self._service.get_backlight_level()
		if level >= 0:
			self._service.set_backlight_level(level + 1)

	def decrease_brightness(self):
		level = self._service.get_backlight_level()
		if level >= 0:
			self._service.set_backlight_level(level - 1)
