import random

class IconLayout:
	def __init__(self, grid):
		self._icons = []
		self._grid = grid

	def add_icon(self, icon):
		self._icons.append(icon)
		self._layout_icon(icon)

	def remove_icon(self, icon):
		self._icons.remove(icon)

	def _layout_icon(self, icon):
		[x1, y1] = self._grid.convert_to_canvas(1, 1)
		[x2, y2] = self._grid.convert_to_canvas(78, 59)
		size = icon.props.size

		x = random.random() * (x2 - x1 - size) 
		y = random.random() * (y2 - y1 - size)

		icon.props.x = x + x1
		icon.props.y = y + y1
