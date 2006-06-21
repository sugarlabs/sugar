import os
import signal
from ConfigParser import ConfigParser

import pygtk
pygtk.require('2.0')
import gtk

from shell import Shell
from sugar import env

class Session:
	def __init__(self):
		self._activity_processes = {}

	def start(self):
		shell = Shell()
		shell.connect('close', self._shell_close_cb)
		shell.start()

		activities = []
		activities_dirs = []
		
		for data_dir in env.get_data_dirs():
			act_dir = os.path.join(data_dir, env.get_activities_dir())
			activities_dirs.append(act_dir)

		activities_dirs.append(os.path.join(env.get_user_dir(), 'activities'))
		
		for activities_dir in activities_dirs:
			if os.path.isdir(activities_dir):
				for filename in os.listdir(activities_dir):
					if filename.endswith(".activity"):
						path = os.path.join(activities_dir, filename)
						cp = ConfigParser()
						cp.read([path])
						python_class = cp.get('Activity', "python_class")
						activities.append(python_class)

		for activity in activities:
			args = [ 'python', '-m', activity ]
			pid = os.spawnvp(os.P_NOWAIT, 'python', args)
			self._activity_processes[activity] = pid

		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
			self.shutdown()
			
	def _shell_close_cb(self, shell):
		self.shutdown()
	
	def shutdown(self):
		# FIXME Obviously we want to notify the activities to
		# shutt down rather then killing them down forcefully.
		for name in self._activity_processes.keys():
			print 'Shutting down %s' % (name) 
			os.kill(self._activity_processes[name], signal.SIGTERM)
