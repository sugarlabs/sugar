import re

import gtk
import goocanvas

class IconItem(goocanvas.Image):
	def __init__(self, icon_name):
		goocanvas.Image.__init__(self)

		self._icon_name = icon_name
		self._color = None

		# FIXME changing the icon color will cause
		# the svg to be read in memory and rendered
		# two times.
		self._update_pixbuf()

	def set_parent(self, parent):
		goocanvas.Image.set_parent(self, parent)

	def set_color(self, color):
		self._color = color
		self._update_pixbuf()

	def _update_pixbuf(self):
		theme = gtk.icon_theme_get_default()
		info = theme.lookup_icon(self._icon_name, 48, 0)
		icon_file = open(info.get_filename(), 'r')
		data = icon_file.read()
		icon_file.close()

		if self._color != None:
			style = '.icon-color {fill: %s;}' % self._color
			data = re.sub('\.icon-color \{.*\}', style, data)

		loader = gtk.gdk.pixbuf_loader_new_with_mime_type('image/svg+xml')
		loader.write(data)
		loader.close()

		self.set_property('pixbuf', loader.get_pixbuf())
