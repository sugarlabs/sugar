import gtk

COLS = 16
ROWS = 12

class Grid(object):
	def __init__(self):
		self._factor = gtk.gdk.screen_width() / COLS

	def point(self, x, y):
		return [x * self._factor, y * self._factor]

	def rectangle(self, x, y, width, height):
		return [x * self._factor, y * self._factor,
				width * self._factor, height * self._factor]
