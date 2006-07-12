import os
import gtk
import sugar.theme

from Shell import Shell
from Process import Process

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
		Process.start(self)
		
		dbus_file = os.fdopen(self._stdout)
		addr = dbus_file.readline()
		addr = addr.strip()
		dbus_file.close()
		os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr

class MatchboxProcess(Process):
	def __init__(self):
		Process.__init__(self, 'matchbox-window-manager -use_titlebar no')
	
	def get_name(self):
		return 'Matchbox'

class Session:
	"""Takes care of running the shell and all the sugar processes"""

	def __init__(self):
		sugar.theme.setup()
		
		self._shell = Shell()
		self._shell.start()

	def start(self):
		"""Start the session"""
		process = DbusProcess()
		process.start()

		process = MatchboxProcess()
		process.start()

		registry = self._shell.get_registry()
		for activity_module in registry.list_activities():
			process = ActivityProcess(activity_module)
			process.start()
		
		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
