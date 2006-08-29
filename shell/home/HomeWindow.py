import gtk
import goocanvas
import cairo

from home.MeshGroup import MeshGroup
from home.HomeGroup import HomeGroup
from home.FriendsGroup import FriendsGroup
import sugar

class HomeWindow(gtk.Window):
	CANVAS_WIDTH = 1200
	CANVAS_HEIGHT = 900
	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

	def set_model(self, model):
		self._model = goocanvas.CanvasModelSimple()
		root = self._model.get_root_item()

		data_model = model.get_mesh()
		self._mesh_group = MeshGroup(data_model)
		root.add_child(self._mesh_group)

		data_model = model.get_friends()
		self._friends_group = FriendsGroup(data_model)
		root.add_child(self._friends_group)

		self._home_group = HomeGroup(self._shell)
		root.add_child(self._home_group)

		canvas = goocanvas.CanvasView()
		canvas.set_bounds(0, 0, HomeWindow.CANVAS_WIDTH,
						  HomeWindow.CANVAS_HEIGHT)
		canvas.set_scale(float(gtk.gdk.screen_width()) /
						 float(HomeWindow.CANVAS_WIDTH))
		canvas.set_size_request(gtk.gdk.screen_width(),
								gtk.gdk.screen_height())
		canvas.set_model(self._model)

		self.add(canvas)
		canvas.show()

	def _set_group_scale(self, group, d):
		x = HomeWindow.CANVAS_WIDTH  * (1 - d) / 2
		y = HomeWindow.CANVAS_HEIGHT * (1 - d) / 2

		matrix = cairo.Matrix(1, 0, 0, 1, 0, 0)
		matrix.translate(x, y)
		matrix.scale(d, d)

		group.set_transform(matrix)

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_HOME:
			self._set_group_scale(self._home_group, 1.0)
		elif level == sugar.ZOOM_FRIENDS:
			self._set_group_scale(self._home_group, 0.5)
			self._set_group_scale(self._friends_group, 1.0)
		elif level == sugar.ZOOM_MESH:
			self._set_group_scale(self._home_group, 0.2)
			self._set_group_scale(self._friends_group, 0.4)
			self._set_group_scale(self._mesh_group, 1.0)
