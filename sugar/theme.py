import gtk

def setup():
	settings = gtk.settings_get_default()
		
	if settings.get_property('gtk-theme-name') != 'olpc':
		settings.set_string_property('gtk-theme-name', 'olpc', '')

	if settings.get_property('gtk-icon-theme-name') != 'olpc':
		settings.set_string_property('gtk-icon-theme-name', 'olpc', '')
