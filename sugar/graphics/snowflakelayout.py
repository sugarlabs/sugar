import math

import cairo

class SnowflakeLayout:
	_BASE_RADIUS = 65
	_CHILDREN_FACTOR = 1
	_FLAKE_DISTANCE = 6

	def __init__(self):
		self._root = None
		self._r = 0

	def set_root(self, icon):
		self._root = icon

	def _layout_root(self, box):
		[width, height] = self._root.get_allocation()

		x = self._cx - (width / 2)
		y = self._cy - (height / 2)

		box.move(self._root, int(x), int(y))

	def _layout_child(self, box, child, index):
		r = self._r
		if (len(box.get_children()) > 10):
			r += SnowflakeLayout._FLAKE_DISTANCE * (index % 3)

		angle = 2 * math.pi / len(box.get_children()) * index

		[width, height] = child.get_allocation()
		x = self._cx + math.cos(angle) * r - (width / 2)
		y = self._cy + math.sin(angle) * r - (height / 2)

		box.move(child, int(x), int(y))

	def get_size(self, box):
		max_child_size = 0
		for child in box.get_children():
			[width, height] = child.get_allocation()
			max_child_size = max (max_child_size, width)
			max_child_size = max (max_child_size, height)

		return self._r * 2 + max_child_size + \
			   SnowflakeLayout._FLAKE_DISTANCE * 2

	def layout(self, box):
		self._r = SnowflakeLayout._BASE_RADIUS + \
				  SnowflakeLayout._CHILDREN_FACTOR * len(box.get_children())

		size = self.get_size(box)
		self._cx = size / 2
		self._cy = size / 2

		self._layout_root(box)

		index = 0
		for child in box.get_children():
			self._layout_child(box, child, index)
			index += 1
