import os
import sys
from ConfigParser import ConfigParser

import pygtk
pygtk.require('2.0')
import gtk

from sugar.shell import shell
from sugar import env

def start(console):
	shell.main()

	activities = []
	
	for data_dir in env.get_data_dirs():
		activities_dir = os.path.join(data_dir, env.get_activities_dir())
		for filename in os.listdir(activities_dir):
			if filename.endswith(".activity"):
				path = os.path.join(activities_dir, filename)

				cp = ConfigParser()
				cp.read([path])
				python_class = cp.get('Activity', "python_class")

				activities.append(python_class)

	for activity in activities:
		args = [ 'python', '-m', activity ]
		if console:
			args.append('--console')
		os.spawnvp(os.P_NOWAIT, 'python', args)

	gtk.main()
