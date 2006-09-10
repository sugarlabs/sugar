import os

from sugar.session.Process import Process
from sugar import env

class MatchboxProcess(Process):
	def __init__(self):
		kbd_config = os.path.join(env.get_data_dir(), 'kbdconfig')
		options = '-kbdconfig %s ' % kbd_config

		options += '-theme olpc '

		command = 'matchbox-window-manager %s ' % options
		Process.__init__(self, command)
	
	def get_name(self):
		return 'Matchbox'
