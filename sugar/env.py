import os
import sys
import pwd

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *

import sugar.setup

def setup_user(profile):
	os.environ['SUGAR_NICK_NAME'] = profile.get_nick_name()

def get_nick_name():
	return os.environ['SUGAR_NICK_NAME']

def setup_python_path():
	for path in sugar_python_path:
		sys.path.insert(0, path)
		if os.environ.has_key('PYTHONPATH'):
			old_path = os.environ['PYTHONPATH']
			os.environ['PYTHONPATH'] = path + ':' + old_path 
		else:
			os.environ['PYTHONPATH'] = path

def setup_system():
	setup_python_path()

	for path in sugar_bin_path:
		if os.environ.has_key('PATH'):
			old_path = os.environ['PATH']
			os.environ['PATH'] = path + ':' + old_path
		else:
			os.environ['PATH'] = path

	if sugar_source_dir:
		source = os.path.join(sugar_source_dir, 'activities')
		runner = os.path.join(sugar_source_dir, 'shell/sugar-activity-factory')
		sugar.setup.setup_activities(source, sugar_activities_dir, runner)
		
		bin = os.path.join(sugar_source_dir, 'shell/sugar-presence-service')
		sugar.setup.write_service('org.laptop.Presence', bin,
								  sugar_activities_dir)

def get_profile_path():
	if os.environ.has_key('SUGAR_PROFILE'):
		profile_id = os.environ['SUGAR_PROFILE']
	else:
		profile_id = 'default'
	path = os.path.expanduser('~/.sugar')

	return os.path.join(path, profile_id)

def get_data_dir():
	return sugar_data_dir

def get_activities_dir():
	return sugar_activities_dir

def get_dbus_config():
	return sugar_dbus_config
