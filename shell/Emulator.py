import os

from Process import Process

class XephyrProcess(Process):
	def __init__(self):
		# FIXME How to pick a free display number?
		self._display = 100
		cmd = 'Xephyr :%d -ac -screen 640x480' % (self._display) 
		Process.__init__(self, cmd)
	
	def get_name(self):
		return 'Xephyr'

	def start(self):
		Process.start(self)
		os.environ['DISPLAY'] = ":%d" % (self._display)

class Emulator:
	"""The OLPC emulator"""

	def __init__(self):
		pass
	
	def start(self):
		process = XephyrProcess()
		process.start()
