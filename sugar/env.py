import os

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *

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
		
def get_data_file(filename):
	for data_dir in get_data_dirs():
		path = os.path.join(data_dir, filename)
		if os.path.isfile(path):
			return path
	return None

def get_data_dirs():
	dirs = []
	for data_dir in data_dirs:
		path = os.path.join(data_basedir, data_dir)
		dirs.append(path)
	return dirs
	
def get_activities_dir():
	return activities_dir
