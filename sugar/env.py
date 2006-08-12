import os
import sys
import pwd

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *

import sugar.setup

def add_to_python_path(path):
	sys.path.insert(0, path)
	if os.environ.has_key('PYTHONPATH'):
		os.environ['PYTHONPATH'] += ':' + path
	else:
		os.environ['PYTHONPATH'] = path

def add_to_bin_path(path):
	if os.environ.has_key('PATH'):
		old_path = os.environ['PATH']
		os.environ['PATH'] = path + ':' + old_path
	else:
		os.environ['PATH'] = path

def setup():
	for path in sugar_python_path:
		add_to_python_path(path)

	for path in sugar_bin_path:
		add_to_bin_path(path)

	if sugar_source_dir:
		source = os.path.join(sugar_source_dir, 'activities')
		runner = os.path.join(sugar_source_dir, 'shell/sugar-activity-factory')
		sugar.setup.setup_activities(source, get_activities_dir(), runner)

def get_user_dir():
	if os.environ.has_key('SUGAR_NICK_NAME'):
		nick = get_nick_name()
		return os.path.expanduser('~/.sugar-%s/' % nick)
	else:
		return os.path.expanduser('~/.sugar')

def get_nick_name():
	if os.environ.has_key('SUGAR_NICK_NAME'):
		return os.environ['SUGAR_NICK_NAME']
	else:
		return pwd.getpwuid(os.getuid())[0]

def get_data_dir():
	return sugar_data_dir

def get_dbus_config():
	return sugar_dbus_config

def get_data_file(filename):
	return os.path.join(get_data_dir(), filename)
		
def get_activities_dir():
	return sugar_activities_dir
