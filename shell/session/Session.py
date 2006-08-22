import os
import gtk
import gobject
import time
import re

from sugar.presence import PresenceService
from Shell import Shell
from ConsoleWindow import ConsoleWindow
from session.Process import Process
import sugar.env

class MatchboxProcess(Process):
	def __init__(self):
		kbd_config = os.path.join(sugar.env.get_data_dir(), 'kbdconfig')
		options = '-kbdconfig %s ' % kbd_config

		options += '-theme olpc '

		command = 'matchbox-window-manager %s ' % options
		Process.__init__(self, command)
	
	def get_name(self):
		return 'Matchbox'

class Session:
	"""Takes care of running the shell and all the sugar processes"""
	def start(self):
		"""Start the session"""

		PresenceService.start()

		process = MatchboxProcess()
		process.start()

		console = ConsoleWindow()
		sugar.logger.start('Shell', console)

		shell = Shell()
		shell.set_console(console)
		shell.start()

		from sugar import TracebackUtils
		tbh = TracebackUtils.TracebackHelper()
		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
		del tbh
