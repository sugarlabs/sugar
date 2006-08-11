import os
import gtk
import gobject
import time
import re

import dbus
import dbus.dbus_bindings

from sugar.presence import PresenceService
from Shell import Shell
from session.Process import Process
import sugar.env

class DbusProcess(Process):
	def __init__(self):
		config = sugar.env.get_dbus_config()
		cmd = "dbus-launch --exit-with-session --config-file %s" % config
		Process.__init__(self, cmd)

	def get_name(self):
		return 'Dbus'

	def start(self):
		Process.start(self, True)
		dbus_file = os.fdopen(self._stdout)
		regexp = re.compile('DBUS_SESSION_BUS_ADDRESS=\'(.*)\'\;')
		addr = regexp.match(dbus_file.readline()).group(1)
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

class PresenceServiceProcess(Process):
	def __init__(self):
		Process.__init__(self, "sugar-presence-service")

	def get_name(self):
		return "PresenceService"

	def start(self):
		Process.start(self)
		bus = dbus.Bus()
		ret = False
		# Wait for the presence service to start up
		while not ret:
			ret = dbus.dbus_bindings.bus_name_has_owner(bus._connection, PresenceService.DBUS_SERVICE)
			time.sleep(0.2)

class Session:
	"""Takes care of running the shell and all the sugar processes"""
	def __init__(self, registry):
		self._registry = registry
		
	def start(self):
		"""Start the session"""
		process = DbusProcess()
		process.start()

		process = MatchboxProcess()
		process.start()

		process = PresenceServiceProcess()
		process.start()

		shell = Shell(self._registry)
		shell.start()

		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
