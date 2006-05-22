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

class Toolbox(gtk.VBox):
	__gsignals__ = {
		'tool-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_STRING])),
		'color-selected': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
						 ([gobject.TYPE_PYOBJECT]))
	}

	def __init__(self):
		gtk.VBox.__init__(self, False, 12)
	
		self._tools_group = None
		self._colors_group = None
		
		self._tool_hbox = gtk.HBox(False, 2)
		
		spring = gtk.Label()
		self._tool_hbox.pack_start(spring, True)
		spring.show()

		self._add_tool('stock_draw-text', 'text')				
		self._add_tool('stock_draw-freeform-line', 'freehand')

		spring = gtk.Label()
		self._tool_hbox.pack_start(spring, True)
		spring.show()
		
		self.pack_start(self._tool_hbox)
		self._tool_hbox.show()
		
		self._color_hbox = gtk.HBox(False, 2)
		
		self._add_color([0, 0, 0])
		self._add_color([1, 0, 0])
		self._add_color([0, 1, 0])
		self._add_color([0, 0, 1])

		self.pack_start(self._color_hbox)		
		self._color_hbox.show()
				
	def _add_tool(self, icon, tool_id):
		image = gtk.Image()
		image.set_from_icon_name(icon, gtk.ICON_SIZE_LARGE_TOOLBAR)
		
		tool = gtk.RadioButton(self._tools_group)
		tool.set_mode(False)
		tool.set_relief(gtk.RELIEF_NONE)
		tool.set_image(image)
		tool.connect('clicked', self.__tool_clicked_cb, tool_id)
		self._tool_hbox.pack_start(tool, False)
		
		if self._tools_group == None:
			self._tools_group = tool
		
		tool.show()

	def _add_color(self, rgb):
		color = ColorButton(self._colors_group, rgb)
		color.connect('clicked', self.__color_clicked_cb, rgb)
		self._color_hbox.pack_start(color, False)

		if self._colors_group == None:
			self._colors_group = color

		color.show()

	def __tool_clicked_cb(self, button, tool_id):
		self.emit("tool-selected", tool_id)
	
	def __color_clicked_cb(self, button, rgb):
		self.emit("color-selected", button.color())

