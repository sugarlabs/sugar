import sys
import logging

import dbus

import sugar.env

class LogWriter:
	def __init__(self, application, use_console = True):
		self._application = application
		self._use_console = use_console
		
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Logger', '/com/redhat/Sugar/Logger')
		self._logger = dbus.Interface(proxy_obj, 'com.redhat.Sugar.Logger')
			
	def start(self):
		if self._use_console:
			sys.stdout = self
			sys.stderr = self

		level = sugar.env.get_logging_level()
		if level == 'debug':
			logging.basicConfig(level=logging.DEBUG,
								format='%(levelname)s %(message)s')

	def write(self, s):
		self._logger.log(self._application, s, ignore_reply=True)

	def emit(self, record):
		pass
	
	def flush(self):
		pass
