import os
import gtk
import gobject
import time
import re

from Shell import Shell
from ConsoleWindow import ConsoleWindow
from session.Process import Process
from FirstTimeDialog import FirstTimeDialog
from sugar import env
from sugar import logger
import conf

class DbusProcess(Process):
	def __init__(self):
		config = env.get_dbus_config()
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
		kbd_config = os.path.join(env.get_data_dir(), 'kbdconfig')
		options = '-kbdconfig %s ' % kbd_config

		options += '-theme olpc '

		command = 'matchbox-window-manager %s ' % options
		Process.__init__(self, command)
	
	def get_name(self):
		return 'Matchbox'

class DBusMonitorProcess(Process):
	def __init__(self):
		Process.__init__(self, "dbus-monitor --session")
	
	def get_name(self):
		return 'dbus-monitor'

class Session:
	"""Takes care of running the shell and all the sugar processes"""

	def _check_profile(self):
		profile = conf.get_profile()

		if profile.get_nick_name() == None:
			dialog = FirstTimeDialog()
			dialog.run()
			profile.save()

		env.setup_user(profile)

	def start(self):
		"""Start the session"""
		process = MatchboxProcess()
		process.start()

		self._check_profile()

		process = DbusProcess()
		process.start()

		if os.environ['SUGAR_DBUS_MONITOR']:
			dbm = DBusMonitorProcess()
			dbm.start()

		console = ConsoleWindow()
		logger.start('Shell', console)

		shell = Shell()
		shell.set_console(console)

		from sugar import TracebackUtils
		tbh = TracebackUtils.TracebackHelper()
		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
		del tbh
