import os
import signal
from ConfigParser import ConfigParser

import pygtk
pygtk.require('2.0')
import gtk

from shell import Shell
from sugar import env
from sugar.activity import Activity

class Session:
	def __init__(self):
		self._activity_processes = {}

	def start(self):
		shell = Shell()
		shell.connect('close', self._shell_close_cb)
		shell.start()
		
		self._run_activities()

		try:
			gtk.main()
		except KeyboardInterrupt:
			print 'Ctrl+C pressed, exiting...'
			self.shutdown()

	def _run_activities(self):
		base_dirs = []
		
		base_dirs.append(env.get_activities_dir())
		base_dirs.append(os.path.join(env.get_user_dir(), 'activities'))

		for base_dir in base_dirs:
			if os.path.isdir(base_dir):
				for filename in os.listdir(base_dir):
					activity_dir = os.path.join(base_dir, filename)
					if os.path.isdir(activity_dir):
						self._run_activity(os.path.abspath(activity_dir))

	def _run_activity(self, activity_dir):
		env.add_to_python_path(activity_dir)

		for filename in os.listdir(activity_dir):
			if filename.endswith(".activity"):
				path = os.path.join(activity_dir, filename)
				cp = ConfigParser()
				cp.read([path])

				activity_name = cp.get('Activity', "name")
				activity_class = cp.get('Activity', "class")

				args = [ 'python', '-m', 'sugar/activity/Activity' ]
				args.append(activity_name)
				args.append(activity_class)
				pid = os.spawnvp(os.P_NOWAIT, 'python', args)
				self._activity_processes[activity_name] = pid

	def _shell_close_cb(self, shell):
		self.shutdown()
	
	def shutdown(self):
		# FIXME Obviously we want to notify the activities to
		# shutt down rather then killing them down forcefully.
		for name in self._activity_processes.keys():
			print 'Shutting down %s' % (name) 
			os.kill(self._activity_processes[name], signal.SIGTERM)
