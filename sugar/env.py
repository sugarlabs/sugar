import os
import sys

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *

def add_to_python_path(path):
	sys.path.insert(0, path)
	if os.environ.has_key('PYTHONPATH'):
		os.environ['PYTHONPATH'] += ':' + path
	else:
		os.environ['PYTHONPATH'] = path

def get_user_dir():
	if os.environ.has_key('SUGAR_USER_DIR'):
		return os.environ['SUGAR_USER_DIR']
	else:
		return os.path.expanduser('~/.sugar/')

def get_logging_level():
	if os.environ.has_key('SUGAR_LOGGING_LEVEL'):
		return os.environ['SUGAR_LOGGING_LEVEL']
	else:
		return 'warning'

def get_nick_name():
	if os.environ.has_key('SUGAR_NICK_NAME'):
		return os.environ['SUGAR_NICK_NAME']
	else:
		return None

def get_data_dir():
	return sugar_data_dir
		
def get_activities_dir():
	return sugar_activities_dir

def get_activity_runner():
	return sugar_activity_runner
