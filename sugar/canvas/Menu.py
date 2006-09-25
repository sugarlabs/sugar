import gtk
import goocanvas
import gobject

from sugar.canvas.CanvasView import CanvasView
from sugar.canvas.CanvasBox import CanvasBox
from sugar.canvas.IconItem import IconItem

class Menu(gtk.Window):
	__gsignals__ = {
		'action': (gobject.SIGNAL_RUN_FIRST,
				   gobject.TYPE_NONE, ([int])),
	}

	def __init__(self, grid, title):
		gtk.Window.__init__(self, gtk.WINDOW_POPUP)

		self._width = 15
		self._height = 0
		self._grid = grid
		self._action_box = None

		self._canvas = CanvasView()
		self.add(self._canvas)
		self._canvas.show()

		model = goocanvas.CanvasModelSimple()
		self._root = model.get_root_item()

		self._rect = goocanvas.Rect(fill_color='black', line_width=0)
		self._root.add_child(self._rect)

		text = goocanvas.Text(text=title, font="Sans bold 18",
							  fill_color='white', anchor=gtk.ANCHOR_SW)
		self._grid.set_constraints(text, 1, 3, self._width, self._height)
		self._root.add_child(text)
		self._height += 1

		self._update_constraints()

		self._canvas.set_model(model)

	def _create_action_box(self):
		separator = goocanvas.Path(data='M 15 0 L 215 0', line_width=3,
								   stroke_color='white')
		self._grid.set_constraints(separator, 0, self._height)
		self._root.add_child(separator)
		self._height += 1

		box = CanvasBox(self._grid, CanvasBox.HORIZONTAL)
		self._grid.set_constraints(box, 0, self._height)
		self._height += 5

		return box

	def get_grid(self):
		return self._grid

	def add_image(self, image_item, width, height):
		"""width & height in grid units"""
		separator = goocanvas.Path(data='M 15 0 L 215 0', line_width=3,
								   stroke_color='white')
		self._grid.set_constraints(separator, 0, self._height)
		self._root.add_child(separator)
		self._height += 1

		self._grid.set_constraints(image_item, x=5, y=self._height, width=width, height=height)
		self._root.add_child(image_item)
		self._height += height
		self._update_constraints()

	def add_action(self, icon, action_id):
		if self._action_box == None:
			self._action_box = self._create_action_box()
			self._root.add_child(self._action_box)
			self._update_constraints()

		icon.connect('clicked', self._action_clicked_cb, action_id)
		self._action_box.set_constraints(icon, 5, 5)
		self._action_box.add_child(icon)

	def _action_clicked_cb(self, icon, action):
		self.emit('action', action)

	def _update_constraints(self):
		self._grid.set_constraints(self._canvas, 0, 0,
								   self._width, self._height)				
		self._grid.set_constraints(self._rect, 0, 0,
								   self._width, self._height)

	def get_width(self):
		return self._width

	def get_height(self):
		return self._height
