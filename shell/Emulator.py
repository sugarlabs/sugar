import logging
import os
import socket

from Process import Process

class XephyrProcess(Process):
	def __init__(self):
		self._display = self.get_display_number()
		cmd = 'Xephyr :%d -ac -screen 640x480' % (self._display) 
		Process.__init__(self, cmd)

	def get_display_number(self):
		"""Find a free display number trying to connect to 6000+ sockets"""
		retries = 20
		display_number = 1
		display_is_free = False
		
		while not display_is_free and retries > 0:
			s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
			try:
				s.connect(('127.0.0.1', 6000 + display_number))
				logging.info('Display %d is already in use. Trying next.' % (display_number))

				display_number += 1
				retries -= 1
			except:
				display_is_free = True

		if display_is_free:
			return display_number
		
		return -1
		
	def get_name(self):
		return 'Xephyr'

	def start(self):
		if self._display < 0:
			logging.error('Cannot find a free display.')
		else:
			Process.start(self)
			os.environ['DISPLAY'] = ":%d" % (self._display)

class Emulator:
	"""The OLPC emulator"""

	def __init__(self):
		pass
	
	def start(self):
		process = XephyrProcess()
		process.start()
