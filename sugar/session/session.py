import os
from ConfigParser import ConfigParser

import pygtk
pygtk.require('2.0')
import gtk

from sugar.shell import shell
from sugar import env

def start():
	shell.main()

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
		os.spawnvp(os.P_NOWAIT, 'python', args)

	try:
		gtk.main()
	except KeyboardInterrupt:
		print 'Ctrl+C pressed, exiting...'
