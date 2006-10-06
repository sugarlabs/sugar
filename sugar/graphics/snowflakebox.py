import math

import cairo
import hippo

_BASE_RADIUS = 65
_CHILDREN_FACTOR = 1
_FLAKE_DISTANCE = 6

class SnowflakeBox(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarSnowflakeBox'
	def __init__(self, **kwargs):
		hippo.CanvasBox.__init__(self, **kwargs)

		self._root = None
		self._r = 0

	def set_root(self, icon):
		self._root = icon

	def _layout_root(self):
		[width, height] = self._root.get_allocation()

		x = self._cx - (width / 2)
		y = self._cy - (height / 2)

		self.move(self._root, int(x), int(y))

	def _layout_child(self, child, index):
		r = self._r
		if (len(self.get_children()) > 10):
			r += _FLAKE_DISTANCE * (index % 3)

		angle = 2 * math.pi / len(self.get_children()) * index

		[width, height] = child.get_allocation()
		x = self._cx + math.cos(angle) * r - (width / 2)
		y = self._cy + math.sin(angle) * r - (height / 2)

		self.move(child, int(x), int(y))

	def do_get_width_request(self):
		hippo.CanvasBox.do_get_width_request(self)

		max_child_size = 0
		for child in self.get_children():
			[width, height] = child.get_allocation()
			max_child_size = max (max_child_size, width)
			max_child_size = max (max_child_size, height)

		return self._r * 2 + max_child_size + _FLAKE_DISTANCE * 2

	def do_get_height_request(self, width):
		hippo.CanvasBox.do_get_height_request(self, width)

		return width

	def do_allocate(self, width, height):
		self._r = _BASE_RADIUS + _CHILDREN_FACTOR * len(self.get_children())

		hippo.CanvasBox.do_allocate(self, width, height)

		self._cx = width / 2
		self._cy = height / 2

		self._layout_root()

		index = 0
		for child in self.get_children():
			self._layout_child(child, index)
			index += 1
