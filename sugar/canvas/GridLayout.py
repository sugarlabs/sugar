import gobject
import goocanvas

class GridConstraints:
	def __init__(self, x, y, width, height, padding=0):
		self.x = x
		self.y = y
		self.width = width
		self.height = height
		self.padding = padding

class GridLayout:
	def __init__(self, cols=16, rows=12):
		self._rows = rows
		self._cols = cols

		self._constraints = {}

	def set_constraints(self, component, constraints):
		self._constraints[component] = constraints

	def _get_geometry(self, container, component):
		constraints = self._constraints[component]
		if constraints:
			return self.get_bounds(container, constraints)
		else:
			return [0, 0, 0, 0]

	def get_bounds(self, container, constraints):
		w = container.props.width
		h = container.props.height
		padding = constraints.padding

		x = constraints.x * w / self._cols + padding
		y = constraints.y * h / self._rows + padding

		width = constraints.width * w / self._cols - padding * 2
		height = constraints.height * h / self._rows - padding * 2

		width = max(0, width)
		height = max(0, height)

		return [x, y, width, height]

	def layout_canvas_group(self, group):
		i = 0
		while i < group.get_n_children():
			item = group.get_child(i)

			[x, y, width, height] = self._get_geometry(group, item)

			item.props.x = x
			item.props.y = y

			try:
				item.props.width = width
				item.props.height = height
			except:
				item.props.size = width

			i += 1

	def layout_screen(self, screen):
		for window in screen.get_windows():
			[x, y, width, height] = self._get_geometry(screen, window)
			window.move(int(x), int(y))
			window.resize(int(width), int(height))

class GridGroup(goocanvas.Group):
	__gproperties__ = {
		'x'    	   : (float, None, None, -10e6, 10e6, 800.0,
					  gobject.PARAM_READWRITE),
		'y'        : (float, None, None, -10e6, 10e6, 600.0,
					  gobject.PARAM_READWRITE),
		'width'    : (float, None, None, 0, 10e6, 800.0,
					  gobject.PARAM_READWRITE),
		'height'   : (float, None, None, 0, 10e6, 600.0,
					  gobject.PARAM_READWRITE)
	}

	def _update_position(self):
		if self._x != 0 or self._y != 0:
			self.translate(self._x, self._y)

	def do_set_property(self, pspec, value):
		if pspec.name == 'width':
			self._width = value
			self._layout.layout_canvas_group(self)
		elif pspec.name == 'height':
			self._height = value
			self._layout.layout_canvas_group(self)
		elif pspec.name == 'x':
			self._x = value
			self._update_position()
		elif pspec.name == 'y':
			self._y = value
			self._update_position()

	def do_get_property(self, pspec):
		if pspec.name == 'width':
			return self._width
		elif pspec.name == 'height':
			return self._height
		elif pspec.name == 'x':
			return self._x
		elif pspec.name == 'x':
			return self._x

	def __init__(self, cols=-1, rows=-1):
		self._x = 0
		self._y = 0
		self._width = 0
		self._height = 0

		goocanvas.Group.__init__(self)

		if rows < 0 and cols < 0:
			self._layout = GridLayout()
		else:
			self._layout = GridLayout(cols, rows)

		self.connect('child-added', self.__child_added_cb)

	def get_layout(self):
		return self._layout

	def __child_added_cb(self, child, position):
		self._layout.layout_canvas_group(self)
