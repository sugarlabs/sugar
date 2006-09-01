import random

class IconLayout:
	def __init__(self, width, height):
		self._icons = []
		self._width = width
		self._height = height

	def set_bounds(self, x1, y1, x2, y2):
		self._x1 = x1
		self._y1 = y1
		self._x2 = x2
		self._y2 = y2

	def add_icon(self, icon):
		self._icons.append(icon)
		self._layout_icon(icon)

	def remove_icon(self, icon):
		self._icons.remove(icon)

	def _is_valid_position(self, icon, x, y):
		icon_size = icon.props.size
		border = 20

		if not (border < x < self._width - icon_size - border and \
		        border < y < self._height - icon_size - border):
			return False
		
		if self._x1 - icon_size - border < x < self._x2 + border and \
		   self._y1 - icon_size - border < y < self._y2 + border:
				return False

		return True

	def _layout_icon(self, icon):
		while True:
			x = random.random() * self._width
			y = random.random() * self._height
			if self._is_valid_position(icon, x, y):
				break

		icon.props.x = x
		icon.props.y = y
