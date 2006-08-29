import gtk
import goocanvas
import cairo

from home.MeshGroup import MeshGroup
from home.HomeGroup import HomeGroup
from home.FriendsGroup import FriendsGroup
import sugar

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell
		self._width = MeshGroup.WIDTH
		self._height = MeshGroup.HEIGHT

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
		self._friends_group.translate((self._width - FriendsGroup.WIDTH) / 2,
									  (self._height - FriendsGroup.HEIGHT) / 2)
		root.add_child(self._friends_group)

		self._home_group = HomeGroup(self._shell)
		self._home_group.translate((self._width - HomeGroup.WIDTH) / 2,
								   (self._height - HomeGroup.HEIGHT) / 2)
		root.add_child(self._home_group)

		self._canvas = goocanvas.CanvasView()
		self._canvas.set_size_request(gtk.gdk.screen_width(),
									  gtk.gdk.screen_height())
		self._canvas.set_model(self._model)

		self.add(self._canvas)
		self._canvas.show()

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_HOME:
			width = HomeGroup.WIDTH * 1.1
			height = HomeGroup.HEIGHT * 1.1
		elif level == sugar.ZOOM_FRIENDS:
			width = FriendsGroup.WIDTH * 1.1
			height = FriendsGroup.HEIGHT * 1.1
		elif level == sugar.ZOOM_MESH:
			width = MeshGroup.WIDTH
			height = MeshGroup.HEIGHT

		self._canvas.set_bounds((self._width - width) / 2,
								(self._height - height) / 2,
								width, height)
		self._canvas.set_scale(gtk.gdk.screen_width() / width)
