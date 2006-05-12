import os

data_dirs = [ 'sugar/browser', 'sugar/chat' ]

def internal_get_data_file(filename):
	basedir = os.path.dirname(os.path.dirname(__file__))
	
	for data_dir in data_dirs:
		path = os.path.abspath(os.path.join(basedir, data_dir, filename))
		if os.path.isfile(path):
			return path
			
	return None
