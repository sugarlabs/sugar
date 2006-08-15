import os
import socket
import sys

from session.Process import Process

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
		cmd = 'Xephyr :%d -ac -screen 640x480' % (self._display) 
		Process.__init__(self, cmd)
		
	def get_name(self):
		return 'Xephyr'

	def start(self):
		Process.start(self)
		os.environ['DISPLAY'] = ":%d" % (self._display)

class XnestProcess(Process):
	def __init__(self):
		self._display = get_display_number()
		cmd = 'Xnest :%d -ac -geometry 693x520' % (self._display) 
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
				print('Cannot run the emulator. You need to install\
					   Xephyr or Xnest.')				
				sys.exit(0)
