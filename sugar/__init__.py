import pygtk
pygtk.require('2.0')
import gtk

settings = gtk.settings_get_default()
	
if settings.get_property('gtk-theme-name') != 'olpc':
	settings.set_string_property('gtk-theme-name', 'olpc', '')

if settings.get_property('gtk-icon-theme-name') != 'olpc':
	settings.set_string_property('gtk-icon-theme-name', 'olpc', '')
