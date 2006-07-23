import os
import gtk
import gobject
import time

from Shell import Shell
from Process import Process
import sugar.theme
import sugar.env

class ActivityProcess(Process):
	def __init__(self, module):
		Process.__init__(self, module.get_exec())
		self._module = module
	
	def get_name(self):
		return self._module.get_name()

class DbusProcess(Process):
	def __init__(self):
		Process.__init__(self, "dbus-daemon --session --print-address")

	def get_name(self):
		return 'Dbus'

	def start(self):
		Process.start(self, True)
		dbus_file = os.fdopen(self._stdout)
		addr = dbus_file.readline()
		addr = addr.strip()
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
		Process.__init__(self, "python shell/PresenceService/PresenceService.py",)

	def get_name(self):
		return "PresenceService"

	def start(self):
		Process.start(self, True)
		time.sleep(3)

class Session:
	"""Takes care of running the shell and all the sugar processes"""

	def __init__(self):
		sugar.theme.setup()
		
	def start(self):
		"""Start the session"""
		process = DbusProcess()
		process.start()

		process = MatchboxProcess()
		process.start()

		process = PresenceServiceProcess()
		process.start()

		shell = Shell()
		shell.start()

		registry = shell.get_registry()
		for activity_module in registry.list_activities():
			process = ActivityProcess(activity_module)
			process.start()
		
		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
