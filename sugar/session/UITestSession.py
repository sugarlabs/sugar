import os

from sugar.session.DbusProcess import DbusProcess
from sugar.session.MatchboxProcess import MatchboxProcess
from sugar.session.Emulator import Emulator
from sugar import env

class UITestSession:
	def start(self):
		env.setup_python_path()

		if os.environ.has_key('SUGAR_EMULATOR') and \
		   os.environ['SUGAR_EMULATOR'] == 'yes':
			emulator = Emulator()
			emulator.start()

		process = MatchboxProcess()
		process.start()

		process = DbusProcess()
		process.start()
