import re

import gobject
import gtk
import goocanvas

from sugar.util import GObjectSingletonMeta

class IconCache(gobject.GObject):
	__metaclass__ = GObjectSingletonMeta

	def __init__(self):
		gobject.GObject.__init__(self)
		self._icons = {}

	def _create_icon(self, name, color, size):
		theme = gtk.icon_theme_get_default()
		info = theme.lookup_icon(name, size, 0)
		icon_file = open(info.get_filename(), 'r')
		data = icon_file.read()
		icon_file.close()

		if color != None:
			style = '.fill-color {fill: %s;}' % color
			data = re.sub('\.fill-color \{.*\}', style, data)

		loader = gtk.gdk.pixbuf_loader_new_with_mime_type('image/svg-xml')
		loader.set_size(size, size)
		loader.write(data)
		loader.close()
		
		return loader.get_pixbuf()

	def get_icon(self, name, color, size):
		key = (name, color, size)
		if self._icons.has_key(key):
			return self._icons[key]
		else:
			icon = self._create_icon(name, color, size)
			self._icons[key] = icon
			return icon

class IconItem(goocanvas.Image):
	def __init__(self, icon_name, color, size, **kwargs):
		goocanvas.Image.__init__(self, **kwargs)

		icon_cache = IconCache()
		pixbuf = icon_cache.get_icon(icon_name, color, size)
		self.set_property('pixbuf', pixbuf)
