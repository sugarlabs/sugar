import logging

import gobject

class Process:
	"""Object representing one of the session processes"""

	def __init__(self, command):
		self._pid = None
		self._command = command
	
	def get_name(self):
		return self._command
	
	def start(self):
		print self._command
		logging.debug('Start %s' % (self._command))

		args = self._command.split()
		flags = gobject.SPAWN_SEARCH_PATH or gobject.SPAWN_STDERR_TO_DEV_NULL
		result = gobject.spawn_async(args, flags=flags, standard_output=True)
		self._pid = result[0]
		self._stdout = result[2]
