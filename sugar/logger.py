import logging

import dbus
import gobject

class Handler(logging.Handler):
	def __init__(self, shell, console_id):
		logging.Handler.__init__(self)

		self._console_id = console_id
		self._shell = shell
		self._messages = []

	def _log(self):
		for message in self._messages:
			# FIXME use a single dbus call
			self._shell.log(self._console_id, message)
		return False

	def emit(self, record):
		self._messages.append(record.msg)
		if len(self._messages) == 1:
			gobject.idle_add(self._log)

def start(console_id, shell = None):
	root_logger = logging.getLogger('')
	root_logger.setLevel(logging.DEBUG)
	
	if shell == None:
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('com.redhat.Sugar.Shell', '/com/redhat/Sugar/Shell')
		shell = dbus.Interface(proxy_obj, 'com.redhat.Sugar.Shell')

	root_logger.addHandler(Handler(shell, console_id))
