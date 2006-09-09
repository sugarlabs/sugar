import goocanvas

from sugar.canvas.GridLayout import GridGroup
from sugar.canvas.GridLayout import GridConstraints

class GridBox(GridGroup, goocanvas.Item):
	__gtype_name__ = 'GridBox'

	VERTICAL = 0
	HORIZONTAL = 1

	def __init__(self, direction, size, padding):
		if direction == GridBox.VERTICAL:
			GridGroup.__init__(self, 1, size)
		else:
			GridGroup.__init__(self, size, 1)

		self._direction = direction
		self._padding = padding

	def _update_constraints(self, item, position):
		if self._direction == GridBox.HORIZONTAL:
			col = position
			row = 0
		else:
			col = 0
			row = position

		constraints = GridConstraints(col, row, 1, 1, self._padding)
		self._layout.set_constraints(item, constraints)

	def do_add_child(self, item, position=-1):
		if position == -1:
			position = self.get_n_children()

		self._update_constraints(item, position)
		
		i = position
		while i < self.get_n_children():
			self._update_constraints(self.get_child(i), i + 1)
			i += 1

		GridGroup.do_add_child(self, item, position)

	def do_remove_child(self, position):
		GridGroup.do_remove_child(self, position)

		i = position
		while i < self.get_n_children():
			self._update_constraints(self.get_child(i), i)
			i += 1
