# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
