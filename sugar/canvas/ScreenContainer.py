import gobject
import gtk

class ScreenContainer(gobject.GObject):
	__gproperties__ = {
		'width'    : (float, None, None, 0, 10e6, 800.0,
					  gobject.PARAM_READABLE),
		'height'   : (float, None, None, 0, 10e6, 600.0,
					  gobject.PARAM_READABLE)
	}

	def __init__(self, windows, **kwargs):
		self._width = gtk.gdk.screen_width()
		self._height = gtk.gdk.screen_height()
		self._windows = windows

		gobject.GObject.__init__(self, **kwargs)

	def do_set_property(self, pspec, value):
		if pspec.name == 'width':
			self._width = value
		elif pspec.name == 'height':
			self._height = value

	def do_get_property(self, pspec):
		if pspec.name == 'width':
			return self._width
		elif pspec.name == 'height':
			return self._height

	def set_layout(self, layout):
		self._layout = layout
		self._layout.layout_screen(self)

	def get_windows(self):
		return self._windows
