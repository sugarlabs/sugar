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

import os
import socket
import sys

import gobject

from sugar import env

def get_display_number():
	"""Find a free display number trying to connect to 6000+ ports"""
	retries = 20
	display_number = 1
	display_is_free = False	

	while not display_is_free and retries > 0:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			s.connect(('127.0.0.1', 6000 + display_number))
			s.close()

			display_number += 1
			retries -= 1
		except:
			display_is_free = True

	if display_is_free:
		return display_number
	else:
		logging.error('Cannot find a free display.')
		sys.exit(0)

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

class MatchboxProcess(Process):
	def __init__(self):
		kbd_config = os.path.join(env.get_data_dir(), 'kbdconfig')
		options = '-kbdconfig %s ' % kbd_config

		options += '-use_titlebar no '
		options += '-theme olpc '

		command = 'matchbox-window-manager %s ' % options
		Process.__init__(self, command)
	
	def get_name(self):
		return 'Matchbox'

class XephyrProcess(Process):
	def __init__(self, fullscreen):
		self._display = get_display_number()
		cmd = 'Xephyr :%d -ac ' % (self._display)
		if fullscreen:
			cmd += '-fullscreen '
		else:
			cmd += '-screen 800x600 '
		Process.__init__(self, cmd)
		
	def get_name(self):
		return 'Xephyr'

	def start(self):
		Process.start(self)
		os.environ['DISPLAY'] = ":%d" % (self._display)

class XnestProcess(Process):
	def __init__(self):
		self._display = get_display_number()
		cmd = 'Xnest :%d -ac -geometry 800x600' % (self._display) 
		Process.__init__(self, cmd)
		
	def get_name(self):
		return 'Xnest'

	def start(self):
		Process.start(self)
		os.environ['DISPLAY'] = ":%d" % (self._display)

class Emulator(object):
	"""The OLPC emulator"""
	def __init__(self, fullscreen):
		self._fullscreen = fullscreen

	def start(self):
		try:
			process = XephyrProcess(self._fullscreen)
			process.start()
		except:
			try:
				process = XnestProcess()
				process.start()
			except:
				print 'Cannot run the emulator. You need to install \
					   Xephyr or Xnest.'
				sys.exit(0)

		process = MatchboxProcess()
		process.start()
