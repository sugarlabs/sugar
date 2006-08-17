import os
import gtk
import gobject
import time
import re

import dbus
import dbus.dbus_bindings

from sugar.presence import PresenceService
from Shell import Shell
from ConsoleWindow import ConsoleWindow
from session.Process import Process
import sugar.env

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

class MatchboxProcess(Process):
	def __init__(self):
		options = '-use_titlebar no'

		kbd_config = os.path.join(sugar.env.get_data_dir(), 'kbdconfig')
		options += ' -kbdconfig %s' % kbd_config

		command = 'matchbox-window-manager %s' % options
		print command
		Process.__init__(self, command)
	
	def get_name(self):
		return 'Matchbox'

class Session:
	"""Takes care of running the shell and all the sugar processes"""
	def __init__(self, registry):
		self._registry = registry
		
	def start(self):
		"""Start the session"""
		process = DbusProcess()
		process.start()

		PresenceService.start()
		bus = dbus.Bus()
		ret = False
		# Wait for the presence service to start up before continuing
		while not ret:
			ret = dbus.dbus_bindings.bus_name_has_owner(bus._connection, PresenceService.DBUS_SERVICE)
			time.sleep(0.2)

		process = MatchboxProcess()
		process.start()

		console = ConsoleWindow()
		sugar.logger.start('Shell', console)

		shell = Shell(self._registry)
		shell.set_console(console)
		shell.start()

		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
