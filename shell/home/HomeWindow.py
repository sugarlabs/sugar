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
		self.set_zoom_level(sugar.ZOOM_HOME)
		model = goocanvas.CanvasModelSimple()
		self._view.set_model(model)

		self.add(self._view)
		self._view.show()

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

	def set_owner(self, owner):
		root = self._view.get_model().get_root_item()

		friends_x = (self._width - FriendsGroup.WIDTH) / 2
		friends_y = (self._height - FriendsGroup.HEIGHT) / 2

		home_x = (self._width - HomeGroup.WIDTH) / 2
		home_y = (self._height - HomeGroup.HEIGHT) / 2

		layout = IconLayout(MeshGroup.WIDTH, MeshGroup.HEIGHT)
		layout.set_internal_bounds(friends_x, friends_y,
								   friends_x + FriendsGroup.WIDTH,
								   friends_y + FriendsGroup.HEIGHT)

		self._mesh_group = MeshGroup(self._shell, layout)
		root.add_child(self._mesh_group)

		layout = IconLayout(FriendsGroup.WIDTH, FriendsGroup.HEIGHT)
		layout.set_internal_bounds(home_x - friends_x, home_y - friends_y,
								   home_x - friends_x + HomeGroup.WIDTH,
								   home_y - friends_y + HomeGroup.HEIGHT)

		friends = owner.get_friends()
		self._friends_group = FriendsGroup(self._shell, friends, layout)
		self._friends_group.translate(friends_x, friends_y)
		root.add_child(self._friends_group)

		self._home_group = HomeGroup(self._shell)
		self._home_group.translate(home_x, home_y)
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
