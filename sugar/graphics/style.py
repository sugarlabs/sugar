_styles = {}

def register_style(name, style):
	_styles[name] = style

def apply_style(name, item):
	if _styles.has_key(name):
		for name in _styles.keys():
			item.set_property(name, _styles[name]

def Style(dict):
	def set_property(self, name, value):
		self._properties[name] = value
