import gtk
import goocanvas
import cairo

class Grid:
	COLS = 80.0
	ROWS = 60.0

	def convert_from_screen(self, x, y):
		factor = Grid.COLS / gtk.gdk.screen_width()
		return [int(x * factor), int(y * factor)]

	def set_constraints(self, component, x, y, width=-1, height=-1):
		if isinstance(component, gtk.Window):
			self._layout_window(component, x, y, width, height)
		elif isinstance(component, goocanvas.Item):
			self._layout_item(component, x, y, width, height)
		elif isinstance(component, goocanvas.CanvasView):
			self._layout_canvas(component, x, y, width, height)

	def _layout_window(self, window, x, y, width, height):
		scale = gtk.gdk.screen_width() / Grid.COLS

		window.move(int(x * scale), int(y * scale))
		window.resize(int(width * scale), int(height * scale))

	def _layout_item(self, item, x, y, width, height):
		scale = 1200 / Grid.COLS

		matrix = cairo.Matrix(1, 0, 0, 1, 0, 0)
		matrix.translate(x * scale, y * scale)
		item.set_transform(matrix)

		# FIXME This is really hacky
		if width > 0 and height > 0:
			try:
				item.props.width = width * scale
				item.props.height = height * scale
			except:
				try:
					item.props.size = width * scale
				except:
					pass

	def _layout_canvas(self, canvas, x, y, width, height):
		scale = 1200 / Grid.COLS

		canvas.set_bounds(x * scale, y * scale, width * scale, height * scale)
