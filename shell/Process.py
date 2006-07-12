import gobject

class Process:
	def __init__(self, command):
		self._pid = None
		self._command = command
	
	def get_name(self):
		return self._command
	
	def start(self):
		args = self._command.split()
		flags = gobject.SPAWN_SEARCH_PATH or gobject.SPAWN_STDERR_TO_DEV_NULL
		result = gobject.spawn_async(args, flags=flags, standard_output=True)
		self._pid = result[0]
		self._stdout = result[2]
