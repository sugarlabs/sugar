try:
	from sugar.__uninstalled__ import internal_get_data_file
except ImportError:
	from sugar.__installed__ import internal_get_data_file
	
def get_data_file(filename):
	return internal_get_data_file(filename)
