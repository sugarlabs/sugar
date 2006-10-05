import gtk

COLS = 16
ROWS = 12

class Grid(object):
	def __init__(self):
		self._factor = gtk.gdk.screen_width() / COLS

	def point(self, grid_x, grid_y):
		return [grid_x * self._factor, grid_y * self._factor]

	def rectangle(self, grid_x, grid_y, grid_w, grid_h):
		return [grid_x * self._factor, grid_y * self._factor,
				grid_w * self._factor, grid_h * self._factor]

	def dimension(self, grid_dimension):
		return grid_dimension * self._factor

	def fit_point(self, x, y):
		return [int(x / self._factor), int(y / self._factor)]
	
