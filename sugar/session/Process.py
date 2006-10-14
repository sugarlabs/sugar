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

import logging

import gobject

class Process:
	"""Object representing one of the session processes"""

	def __init__(self, command):
		self._command = command
	
	def get_name(self):
		return self._command
	
	def start(self, standard_output=False):
		args = self._command.split()
		flags = gobject.SPAWN_SEARCH_PATH
		result = gobject.spawn_async(args, flags=flags,
									 standard_output=standard_output)
		self._stdout = result[2]
