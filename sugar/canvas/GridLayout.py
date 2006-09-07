class GridConstraints:
	def __init__(x, y, width, height):
		self.x = x
		self.y = y
		self.width = width
		self.height = height

class GridLayout:
	def __init__(self, rows, cols):
		self._rows = rows
		self._cols = cols

		self._constraints = {}

	def set_constraints(component, constraints):
		self._constraints[component] = constraints

	def _get_geometry(self, container, component):
		constraints = self._constraints[component]
		if constraints:
			x = constraints.x * component.props.width / self._rows
			y = constraints.y * component.props.height / self._cols
			width = constraints.width * component.props.width / self._rows
			height = constraints.height * component.props.height / self._cols

			return [x, y, width, height]
		else:
			return [0, 0, 0, 0]

	def layout_canvas_group(group):
		i = 0
		while i < group.get_n_children():
			item = group.get_child(i)

			[x, y, width, height] = self._get_geometry(group, item)

			item.props.x = x
			item.props.y = y
			item.props.width = width
			item.props.height = height
