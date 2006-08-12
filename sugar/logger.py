import sys
import logging
import traceback
from cStringIO import StringIO

import dbus
import gobject

__console = None
__console_id = None

class Handler(logging.Handler):
	def __init__(self, console, console_id):
		logging.Handler.__init__(self)

		self._console_id = console_id
		self._console = console
		self._records = []
		self._console_started = False

		bus = dbus.SessionBus()
		bus.add_signal_receiver(self.__name_owner_changed,
								dbus_interface = "org.freedesktop.DBus",
								signal_name = "NameOwnerChanged")

	def __name_owner_changed(self, service_name, old_name, new_name):
		if new_name != None:
			self._console_started = True
		else:
			self._console_started = False

	def _log(self):
		if not self._console_started:
			return True

		for record in self._records:
			self._console.log(record.levelno, self._console_id, record.msg)
		self._records = []

		return False

	def emit(self, record):
		self._records.append(record)
		if len(self._records) == 1:
			gobject.idle_add(self._log)

def __exception_handler(typ, exc, tb):
	trace = StringIO()
	traceback.print_exception(typ, exc, tb, None, trace)

	__console.log(logging.ERROR, __console_id, trace.getvalue())

def start(console_id, console = None):
	root_logger = logging.getLogger('')
	root_logger.setLevel(logging.DEBUG)
	
	if console == None:
		bus = dbus.SessionBus()
		proxy_obj = bus.get_object('org.laptop.Sugar.Console',
								   '/org/laptop/Sugar/Console')
		console = dbus.Interface(proxy_obj, 'org.laptop.Sugar.Console')

	root_logger.addHandler(Handler(console, console_id))

	global __console
	global __console_id

	__console = console
	__console_id = console_id
	sys.excepthook = __exception_handler
