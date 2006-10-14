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

from sugar.session.Process import Process
import sugar.env

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

class XephyrProcess(Process):
	def __init__(self):
		self._display = get_display_number()
		cmd = 'Xephyr :%d -ac -screen 800x600' % (self._display) 
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

class Emulator:
	"""The OLPC emulator"""
	def start(self):
		try:
			process = XephyrProcess()
			process.start()
		except:
			try:
				process = XnestProcess()
				process.start()
			except:
				print 'Cannot run the emulator. You need to install \
					   Xephyr or Xnest.'
				sys.exit(0)
