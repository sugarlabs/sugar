import re

import gobject
import gtk
import goocanvas
import rsvg

class IconView(goocanvas.ItemViewSimple):
	def __init__(self, handle, canvas_view, parent_view):
		goocanvas.SimpleItemView.__init__(self, canvas_view, parent_view)
		self._handle = handle

	def do_paint(self, cr, bounds, scale):
		self._handle.render_cairo(cr)
		return self.bounds

class IconItem(goocanvas.Image):
	__gproperties__ = {
		'icon-name': (str, None, None, None, gobject.PARAM_READWRITE),
		'color': (str, None, None, None, gobject.PARAM_READWRITE)
	}

	def __init__(self, **kwargs):
		goocanvas.Image.__init__(self, **kwargs)

	def do_set_property(self, pspec, value):
		if pspec.name == 'icon-name':
			self._icon_name = value
		elif pspec.name == 'color':
			self._color = value
		else:
			raise AttributeError, 'unknown property %s' % pspec.name

	def do_get_property(self, pspec):
		if pspec.name == 'icon-name':
			return self._icon_name
		if pspec.name == 'color':
			return self._color

	def create_view(self, canvas_view, parent_view):
		print 'Create view'
		theme = gtk.icon_theme_get_default()
		info = theme.lookup_icon(self._icon_name, 48, 0)
		icon_file = open(info.get_filename(), 'r')
		data = icon_file.read()
		icon_file.close()

		if self._color != None:
			style = '.icon-color {fill: %s;}' % self._color
			data = re.sub('\.icon-color \{.*\}', style, data)

		handle = rsvg.Handle(data=data)

		return IconView(handle, canvas_view, parent_view)
