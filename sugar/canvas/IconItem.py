import re

import gobject
import gtk
import goocanvas

from sugar.util import GObjectSingletonMeta
from sugar.canvas.IconColor import IconColor

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
			fill = color.get_fill_color()
			stroke = color.get_stroke_color()

			style = '.fill {fill:%s;stroke:%s;}' % (fill, fill)
			data = re.sub('\.fill \{.*\}', style, data)

			style = '.shape {stroke:%s;fill:%s;}' % (stroke, stroke)
			data = re.sub('\.shape \{.*\}', style, data)

			style = '.shape-and-fill {fill:%s; stroke:%s;}' % (fill, stroke)
			data = re.sub('\.shape-and-fill \{.*\}', style, data)

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
	__gproperties__ = {
		'icon-name': (str, None, None, None,
					  gobject.PARAM_CONSTRUCT_ONLY |
					  gobject.PARAM_READWRITE),
		'color'    : (object, None, None,
					  gobject.PARAM_CONSTRUCT_ONLY |
					  gobject.PARAM_READWRITE),
		'size'     : (int, None, None,
					  0, 1024, 24,
					  gobject.PARAM_CONSTRUCT_ONLY |
					  gobject.PARAM_READWRITE)
	}

	def do_set_property(self, pspec, value):
		if pspec.name == 'icon-name':
			self._icon_name = value
		elif pspec.name == 'color':
			self._color = value
		elif pspec.name == 'size':
			self._size = value

	def __init__(self, **kwargs):
		goocanvas.Image.__init__(self, **kwargs)

		if self._color:
			cache = IconCache()
			pixbuf = cache.get_icon(self._icon_name, self._color, self._size)
			self.props.pixbuf = pixbuf
		else:
			theme = gtk.icon_theme_get_default()
			pixbuf = theme.load_icon(self._icon_name, self._size, 0)
			self.props.pixbuf = pixbuf
