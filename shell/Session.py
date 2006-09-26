import os
import gtk

from view.Shell import Shell
from model.ShellModel import ShellModel
from sugar import env
from sugar import logger

from sugar.session.Process import Process
from sugar.session.DbusProcess import DbusProcess
from sugar.session.MatchboxProcess import MatchboxProcess

from view.FirstTimeDialog import FirstTimeDialog
import conf

class DBusMonitorProcess(Process):
	def __init__(self):
		Process.__init__(self, "dbus-monitor --session")
	
	def get_name(self):
		return 'dbus-monitor'

class Session:
	"""Takes care of running the shell and all the sugar processes"""

	def _check_profile(self):
		profile = conf.get_profile()

		name = profile.get_nick_name() 
		if not name or not len(name):
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

		if os.environ.has_key('SUGAR_DBUS_MONITOR'):
			dbm = DBusMonitorProcess()
			dbm.start()

		model = ShellModel()
		shell = Shell(model)

		from sugar import TracebackUtils
		tbh = TracebackUtils.TracebackHelper()
		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
		del tbh
