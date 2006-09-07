import goocanvas

from sugar.canvas.GridLayout import GridGroup

# FIXME model subclassing doesn't work in pygoocanvas

class GridModel:
	def __init__(self, bg_color):
		self._model = goocanvas.CanvasModelSimple()

		self._width = 800
		self._height = 600

		item = goocanvas.Rect(width=self._width, height=self._height,
							  line_width=0, fill_color=bg_color)
		self._model.get_root_item().add_child(item)

		self._root = GridGroup()
		self._root.props.width = self._width
		self._root.props.height = self._height
		self._model.get_root_item().add_child(self._root)

	def add(self, child):
		self._root.add_child(child)

	def get(self):
		return self._model

	def get_width(self):
		return self._width

	def get_bounds(self, constraints):
		return self.get_layout().get_bounds(self._root, constraints)

	def get_layout(self):
		return self._root.get_layout()
