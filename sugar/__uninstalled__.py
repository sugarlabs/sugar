import os

basedir = os.path.dirname(os.path.dirname(__file__))
data_dirs = [ 'sugar/browser', 'sugar/chat' ]

def internal_get_data_file(filename):
	for data_dir in data_dirs:
		path = os.path.abspath(os.path.join(basedir, data_dir, filename))
		if os.path.isfile(path):
			return path
			
	return None
