import os

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *
		
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
