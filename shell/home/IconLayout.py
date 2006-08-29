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

	def _is_valid_position(self, x, y):
		if x < self._x1 or x > self._x2:
			return True
		if y < self._y1 or y > self._y2:
			return True
		return False

	def _layout_icon(self, icon):
		while True:
			x = random.random() * self._width
			y = random.random() * self._height
			if self._is_valid_position(x, y):
				break

		icon.props.x = x
		icon.props.y = y
