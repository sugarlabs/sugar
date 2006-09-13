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

	def _layout(self):
		x = self._padding
		y = self._padding

		i = 0
		while i < self.get_n_children():
			item = self.get_child(i)
			[width, height] = self._constraints[item]

			self._grid.set_constraints(item, x, y, width, height)

			if self._orientation == CanvasBox.VERTICAL:
				y += height + self._padding
			else:
				x += width + self._padding

			i += 1

	def _child_added_cb(self, item, position):
		self._layout()

	def _child_removed_cb(self, item, position):
		self._layout()
