import gtk
import goocanvas
import cairo

from sugar.canvas.IconItem import IconItem

class Grid:
	COLS = 80.0
	ROWS = 60.0

	def convert_from_screen(self, x, y):
		factor = Grid.COLS / gtk.gdk.screen_width()

		grid_x = round(x * factor) - 1
		grid_y = round(y * factor) - 1

		return [grid_x, grid_y]

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

		self._allocate_item_position(item, x * scale, y * scale)
		if width > 0 and height > 0:
			self._allocate_item_size(item, width * scale, height * scale)

	# FIXME We really need layout support in goocanvas
	def _allocate_item_size(self, item, width, height):
		if isinstance(item, goocanvas.Rect):
			item.props.width = width - (item.props.line_width - 1) * 2
			item.props.height = height - (item.props.line_width - 1) * 2
		elif isinstance(item, goocanvas.Text):
			item.props.width = width
		elif isinstance(item, IconItem):
			item.props.size = width

	def _allocate_item_position(self, item, x, y):
		if isinstance(item, goocanvas.Rect):
			x = x + (item.props.line_width - 1)
			y = y + (item.props.line_width - 1)

		matrix = cairo.Matrix(1, 0, 0, 1, 0, 0)
		matrix.translate(x, y)
		item.set_transform(matrix)

	def _layout_canvas(self, canvas, x, y, width, height):
		scale = 1200 / Grid.COLS
		canvas.set_bounds(x * scale, y * scale, width * scale, height * scale)
