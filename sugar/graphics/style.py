_styles = {}

def register_stylesheet(name, style):
	_styles[name] = style

def apply_stylesheet(item, stylesheet_name):
	if _styles.has_key(stylesheet_name):
		style_sheet = _styles[stylesheet_name]
		for name in style_sheet.keys():
			item.set_property(name, style_sheet[name])
