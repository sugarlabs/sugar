import os
import signal

import gobject

from Shell import Shell

class Process:
	def __init__(self, command):
		self._pid = None
		self._command = command
	
	def get_name(self):
		return self._command
	
	def start(self):
		splitted_cmd = self._command.split()
		try:
			self._pid = os.spawnvp(os.P_NOWAIT, splitted_cmd[0], splitted_cmd)
		except Exception, e:
			logging.error('Cannot run %s' % (self.get_name()))

	def stop(self):
		# FIXME Obviously we want to notify the processes to
		# shut down rather then killing them down forcefully.
		print 'Stopping %s (%d)' % (self.get_name(), self._pid) 
		os.kill(self._pid, signal.SIGTERM)

class ActivityProcess(Process):
	def __init__(self, module):
		Process.__init__(self, module.get_exec())
		self._module = module
	
	def get_name(self):
		return self._module.get_name()

class DbusProcess(Process):
	def __init__(self):
		Process.__init__(self, "/bin/dbus-daemon --session --print-address")

	def get_name(self):
		return 'Dbus'

	def start(self):
		args = self._command.split()
		(self._pid, ign1, dbus_stdout, ign3) = gobject.spawn_async(
			args, flags=gobject.SPAWN_STDERR_TO_DEV_NULL, standard_output=True)

		dbus_file = os.fdopen(dbus_stdout)
		addr = dbus_file.readline()
		addr = addr.strip()
		dbus_file.close()
		os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr

class MatchboxProcess(Process):
	def __init__(self):
		Process.__init__(self, 'matchbox-window-manager -use_titlebar no')
	
	def get_name(self):
		return 'Matchbox'

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

class Session:
	"""Takes care of running the shell and all the sugar processes"""

	def __init__(self):
		self._processes = []

		self._shell = Shell()
		self._shell.connect('close', self._shell_close_cb)
		self._shell.start()

	def start(self):
		"""Start the session"""
		# FIXME We should not start this on the olpc
		process = XephyrProcess()
		self._processes.insert(0, process)
		process.start()

		process = DbusProcess()
		self._processes.insert(0, process)
		process.start()

		process = MatchboxProcess()
		self._processes.insert(0, process)
		process.start()

		registry = self._shell.get_registry()
		for activity_module in registry.list_activities():
			process = ActivityProcess(activity_module)
			self._processes.insert(0, process)
			process.start()

		try:
			import gtk
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
			self.shutdown()

	def _shell_close_cb(self, shell):
		self.shutdown()

	def shutdown(self):
		for process in self._processes:
			process.stop()
