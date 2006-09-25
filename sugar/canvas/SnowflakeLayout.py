import math

import cairo

class SnowflakeLayout:
	_BASE_RADIUS = 65
	_CHILDREN_FACTOR = 1
	_FLAKE_DISTANCE = 6
	_BORDER = 20

	def __init__(self):
		self._root = None
		self._children = []
		self._size = 0

	def set_root(self, icon):
		self._root = icon

	def add_child(self, icon):
		self._children.append(icon)
		self._layout()

	def remove_child(self, icon):
		self._children.remove(icon)
		self._layout()

	def _layout_root(self):
		[width, height] = self._root.get_size_request()

		matrix = cairo.Matrix(1, 0, 0, 1, 0, 0)
		matrix.translate(self._cx, self._cy)
		self._root.set_transform(matrix)

	def _layout_child(self, child, index):
		r = self._r
		if (len(self._children) > 10):
			r += SnowflakeLayout._FLAKE_DISTANCE * (index % 3)

		angle = 2 * math.pi / len(self._children) * index

		x = self._cx + math.cos(angle) * r
		y = self._cy + math.sin(angle) * r

		matrix = cairo.Matrix(1, 0, 0, 1, 0, 0)
		matrix.translate(x, y)
		child.set_transform(matrix)

	def get_size(self):
		return self._size

	def _layout(self):
		self._r = SnowflakeLayout._BASE_RADIUS + \
				  SnowflakeLayout._CHILDREN_FACTOR * len(self._children)
		self._size = self._r * 2 + SnowflakeLayout._BORDER + \
					 SnowflakeLayout._FLAKE_DISTANCE * 2 

		self._cx = self._size / 2
		self._cy = self._size / 2

		self._layout_root()

		index = 0
		for child in self._children:
			self._layout_child(child, index)
			index += 1
