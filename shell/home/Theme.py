import gobject



class Theme(gobject.GObject):
	__gsignals__ = {
		'theme-changed':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
					       ([]))
	}

	# from OLPC_PLAN_14.swf
	__colors = {
		'blue':      ("#c7d2fb", "#bbc8fa", "#afbffa"),
		'turquoise': ("#c8dce8", "#bdd4e3", "#b1cdde"),
		'green':     ("#ccebac", "#c1e79a", "#b6e388"),
		'tan':       ("#e8ead1", "#e4e5c8", "#dfe1be"),
		'gray':      ("#dbe1dd", "#d3dbd5", "#ccd5ce"),
		'dark-gray': ("#dad1d4", "#d2c7cb", "#cabdc2")
	}

	def __init__(self):
		gobject.GObject.__init__(self)
		self._cur_theme = 'blue'

	def set(self, theme):
		updated = False
		if type(theme) == type(""):
			theme = theme.lower()
			if self.__colors.has_key(theme):
				self._cur_theme = theme
				updated = True
		elif type(theme) == type(1):
			try:
				theme = self.__colors.keys()[theme]
				self._cur_theme = theme
				updated = True
			except IndexError:
				pass
		if updated:
			self.emit('theme-changed')

	def get_home_activities_color(self):
		return self.__colors[self._cur_theme][0]

	def get_home_friends_color(self):
		return self.__colors[self._cur_theme][1]

	def get_home_mesh_color(self):
		return self.__colors[self._cur_theme][2]

# Use this accessor, don't create more than one theme object
_theme = None
def get_instance():
	global _theme
	if not _theme:
		_theme = Theme()
	return _theme
