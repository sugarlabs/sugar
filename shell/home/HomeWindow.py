import gtk
import goocanvas
import cairo

from home.MeshGroup import MeshGroup
from home.HomeGroup import HomeGroup
from home.FriendsGroup import FriendsGroup
from home.IconLayout import IconLayout
import sugar

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell
		self._width = MeshGroup.WIDTH
		self._height = MeshGroup.HEIGHT

		self._view = goocanvas.CanvasView()
		self._view.set_size_request(gtk.gdk.screen_width(),
									gtk.gdk.screen_height())

		model = goocanvas.CanvasModelSimple()
		self._view.set_model(model)

		self.add(self._view)
		self._view.show()

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

	def set_model(self, model):
		root = self._view.get_model().get_root_item()

		icon_layout = IconLayout(MeshGroup.WIDTH, MeshGroup.HEIGHT)
		x1 = (self._width - FriendsGroup.WIDTH) / 2
		y1 = (self._height - FriendsGroup.HEIGHT) / 2
		x2 = x1 + FriendsGroup.WIDTH
		y2 = y1 + FriendsGroup.HEIGHT
		icon_layout.set_bounds(x1, y1, x2, y2)

		data_model = model.get_mesh()
		self._mesh_group = MeshGroup(self._shell, icon_layout, data_model)
		root.add_child(self._mesh_group)

		icon_layout = IconLayout(FriendsGroup.WIDTH, FriendsGroup.HEIGHT)
		x1 = (self._width - HomeGroup.WIDTH) / 2
		y1 = (self._height - HomeGroup.HEIGHT) / 2
		x2 = x1 + HomeGroup.WIDTH
		y2 = y1 + HomeGroup.HEIGHT
		icon_layout.set_bounds(x1, y1, x2, y2)

		data_model = model.get_friends()
		self._friends_group = FriendsGroup(icon_layout, data_model)
		self._friends_group.translate((self._width - FriendsGroup.WIDTH) / 2,
									  (self._height - FriendsGroup.HEIGHT) / 2)
		root.add_child(self._friends_group)

		self._home_group = HomeGroup(self._shell)
		self._home_group.translate((self._width - HomeGroup.WIDTH) / 2,
								   (self._height - HomeGroup.HEIGHT) / 2)
		root.add_child(self._home_group)

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

		self._view.set_bounds((self._width - width) / 2,
							  (self._height - height) / 2,
							  width, height)
		self._view.set_scale(gtk.gdk.screen_width() / width)
