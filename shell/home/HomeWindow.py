import gtk

from home.MeshView import MeshView
from home.HomeView import HomeView
from home.FriendsView import FriendsView

class HomeWindow(gtk.Window):
	HOME_VIEW = 0
	FRIENDS_VIEW = 1
	MESH_VIEW = 2

	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell

		self.connect('realize', self.__realize_cb)

		self._nb = gtk.Notebook()
		self._nb.set_show_tabs(False)
		self._nb.set_show_border(False)

		self.add(self._nb)
		self._nb.show()

	def set_model(self, model):
		home_view = HomeView(self._shell)
		self._nb.append_page(home_view)
		self._setup_canvas(home_view)
		home_view.show()

		friends_view = FriendsView(self._shell, model.get_friends())
		self._nb.append_page(friends_view)
		self._setup_canvas(friends_view)
		friends_view.show()
		
		mesh_view = MeshView(self._shell, model.get_mesh())
		self._setup_canvas(mesh_view)
		self._nb.append_page(mesh_view)
		mesh_view.show()

	def set_view(self, view):
		self._nb.set_current_page(view)

	def _setup_canvas(self, canvas):
		canvas.set_bounds(0, 0, 1200, 900)
		canvas.set_scale(float(gtk.gdk.screen_width()) / float(1200))
		canvas.set_size_request(gtk.gdk.screen_width(), gtk.gdk.screen_height())

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
