import random

from sugar.canvas import Colors

def is_valid(fill_color):
	return Colors.table.has_key(fill_color)

class IconColor:
	def __init__(self, fill_color=None):
		if fill_color == None:
			n = int(random.random() * (len(Colors.table) - 1))
			fill_color = Colors.table.keys()[n]
		else:
			if fill_color[0] == '#':
				fill_color = fill_color.upper()
			else:
				fill_color = fill_color.lower()
			if not Colors.table.has_key(fill_color):
				raise RuntimeError("Specified fill color %s is not allowed." % fill_color)
		self._fill_color = fill_color

	def get_stroke_color(self):
		return Colors.table[self._fill_color]

	def get_fill_color(self):
		return self._fill_color
