import logging

import gobject

class Process:
	"""Object representing one of the session processes"""

	def __init__(self, command):
		self._command = command
	
	def get_name(self):
		return self._command
	
	def start(self, standard_output=False):
		args = self._command.split()
		flags = gobject.SPAWN_SEARCH_PATH
		result = gobject.spawn_async(args, flags=flags,
									 standard_output=standard_output)
		self._stdout = result[2]
