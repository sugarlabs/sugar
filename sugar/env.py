import os

try:
	from sugar.__uninstalled__ import *
except ImportError:
	from sugar.__installed__ import *
	
def get_data_file(filename):
	return internal_get_data_file(filename)
