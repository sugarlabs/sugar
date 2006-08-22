import os
import socket
import sys

from session.Process import Process
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

class DbusProcess(Process):
	def __init__(self):
		config = sugar.env.get_dbus_config()
		cmd = "dbus-daemon --print-address --config-file %s" % config
		Process.__init__(self, cmd)

	def get_name(self):
		return 'Dbus'

	def start(self):
		Process.start(self, True)
		dbus_file = os.fdopen(self._stdout)
		addr = dbus_file.readline().strip()
		dbus_file.close()
		os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr

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

		process = DbusProcess()
		process.start()
