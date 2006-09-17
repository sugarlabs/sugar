import goocanvas

class CanvasBox(goocanvas.Group):
	VERTICAL = 0
	HORIZONTAL = 1

	def __init__(self, grid, orientation, padding=0):
		goocanvas.Group.__init__(self)

		self._grid = grid
		self._orientation = orientation
		self._padding = padding
		self._constraints = {}

		self.connect('child-added', self._child_added_cb)
		self.connect('child-removed', self._child_removed_cb)

	def set_constraints(self, item, width, height):
		self._constraints[item] = [width, height]

	def _layout(self, start_item):
		if start_item == -1:
			start_item = self.get_n_children() - 1

		pos = 0
		i = 0
		while i < self.get_n_children():
			item = self.get_child(i)
			[width, height] = self._constraints[item]

			pos += self._padding

			if self._orientation == CanvasBox.VERTICAL:
				x = self._padding
				y = pos
				pos += height + self._padding
			else:
				x = pos
				y = self._padding
				pos += width + self._padding

			if i >= start_item:
				self._grid.set_constraints(item, x, y, width, height)

			i += 1

	def _child_added_cb(self, item, position):
		self._layout(position)

	def _child_removed_cb(self, item, position):
		self._layout(position)
