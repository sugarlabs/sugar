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

import sys, os
import logging
import traceback
from cStringIO import StringIO

import dbus

#internals of D-Bus Python are changing
#try not to use it in the future
if dbus.version < (0, 70, 0):
	import dbus.dbus_bindings

import gobject

from sugar import env

__queue = None

CONSOLE_BUS_NAME = 'org.laptop.Sugar.Console'
CONSOLE_OBJECT_PATH = '/org/laptop/Sugar/Console'
CONSOLE_IFACE = 'org.laptop.Sugar.Console'

class MessageQueue:
	def __init__(self, console, console_id):
		self._idle_id = 0
		self._console = console
		self._console_id = console_id
		self._levels = []
		self._messages = []
		self._bus = dbus.SessionBus()
		
		if self._console == None:
			con = self._bus._connection
			name_has_owner = False
			
			try:
				name_has_owner = dbus.dbus_bindings.bus_name_has_owner(con, CONSOLE_BUS_NAME)
			except:
				name_has_owner = con.name_has_owner(CONSOLE_BUS_NAME)

			if name_has_owner:
				self.setup_console()
			else:
				self._bus.add_signal_receiver(
									self.__name_owner_changed,
									dbus_interface = "org.freedesktop.DBus",
									signal_name = "NameOwnerChanged")

	def setup_console(self):
		proxy_obj = self._bus.get_object(CONSOLE_BUS_NAME,
										 CONSOLE_OBJECT_PATH)
		self._console = dbus.Interface(proxy_obj, CONSOLE_IFACE)
		self._queue_log()

	def __name_owner_changed(self, service_name, old_name, new_name):
		if service_name == CONSOLE_BUS_NAME:
			if new_name != None:
				self.setup_console()
			else:
				self._console = None

	def _queue_log(self):
		if self._idle_id == 0:
			self._idle_id = gobject.idle_add(self._log)

	def _log(self):
		# Use stderr for now until dbus issues get sorted out
		use_dbus = False

		if use_dbus:
			if self._console == None or len(self._messages) == 0:
				self._idle_id = 0
				return False

			if isinstance(self._console, dbus.Interface):
				self._console.log(self._console_id, self._levels,
								  self._messages, timeout = 1000)
			else:
				self._console.log(self._console_id, self._levels,
								  self._messages)
		else:
			for x in range(0, len(self._messages)):
				level = self._levels[x]
				msg = self._messages[x]
				prog = os.path.basename(sys.argv[0])
				fmt = "%s (%s): Level %s - %s\n" % (prog, os.getpid(), level, msg)
				fmt = fmt.encode("utf8")
				sys.stderr.write(fmt)

		self._levels = []
		self._messages = []
		self._idle_id = 0

		return False

	def append_record(self, record):
		self.append(record.levelno, record.msg)

	def append(self, level, message):
		self._levels.append(level)
		self._messages.append(message)
		self._queue_log()

class Handler(logging.Handler):
	def __init__(self, queue):
		logging.Handler.__init__(self)

		self._queue = queue

	def emit(self, record):
		self._queue.append_record(record)

def __exception_handler(typ, exc, tb):
	trace = StringIO()
	traceback.print_exception(typ, exc, tb, None, trace)
	print >> sys.stderr, trace.getvalue()

	__queue.append(logging.ERROR, trace.getvalue())

def start(console_id, console = None):
	queue = MessageQueue(console, console_id)

	root_logger = logging.getLogger('')
	root_logger.setLevel(logging.DEBUG)
	root_logger.addHandler(Handler(queue))

	log_file = os.path.join(env.get_profile_path(), 'sugar.log')
	fileh = logging.FileHandler(log_file)
	fileh.setFormatter(logging.Formatter("""[%(asctime)s] %(message)s"""))
	root_logger.addHandler(fileh)

	global __queue
	__queue = queue
	sys.excepthook = __exception_handler
