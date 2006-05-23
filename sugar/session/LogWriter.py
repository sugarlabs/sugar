import os
import sys

import dbus

class LogWriter:
	def __init__(self, application):
		self._application = application
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Logger', '/com/redhat/Sugar/Logger')
		self._logger = dbus.Interface(proxy_obj, 'com.redhat.Sugar.Logger')

	def start(self):
		if os.environ.has_key('SUGAR_USE_CONSOLE'):
			sys.stdout = self
			sys.stderr = self

	def write(self, s):
		try:
			self._logger.log(self._application, s)
		except:
			pass
