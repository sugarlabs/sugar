import pygtk
pygtk.require('2.0')
import gtk
import gobject

class ColorButton(gtk.RadioButton):
	def __init__(self, group, rgb):
		gtk.RadioButton.__init__(self, group)
		
		self._rgb = rgb
		
		self.set_mode(False)
		self.set_relief(gtk.RELIEF_NONE)
		
		drawing_area = gtk.DrawingArea()
		drawing_area.set_size_request(16, 16)
		drawing_area.connect('expose_event', self.expose)
		self.add(drawing_area)
		drawing_area.show()

	def color(self):
		return self._rgb

	def expose(self, widget, event):
		rect = widget.get_allocation()
		ctx = widget.window.cairo_create()

		ctx.set_source_rgb(self._rgb[0], self._rgb[1] , self._rgb[2])
		ctx.rectangle(0, 0, rect.width, rect.height)
		ctx.fill()
		
		return False

class Toolbox(gtk.HBox):
	__gsignals__ = {
		'color-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gtk.HBox.__init__(self, False, 6)
	
		self._colors_group = None
		
		self._add_color([0, 0, 0])
		self._add_color([1, 0, 0])
		self._add_color([0, 1, 0])
		self._add_color([0, 0, 1])
				
	def _add_color(self, rgb):
		color = ColorButton(self._colors_group, rgb)
		color.connect('clicked', self.__color_clicked_cb, rgb)
		self.pack_start(color, False)

		if self._colors_group == None:
			self._colors_group = color

		color.show()

	def __color_clicked_cb(self, button, rgb):
		self.emit("color-selected", button.color())
