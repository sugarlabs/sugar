import gtk

from home.MeshView import MeshView
from home.HomeView import HomeView

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)

		self.connect('realize', self.__realize_cb)

		self._nb = gtk.Notebook()
		self._nb.set_show_tabs(False)
		self._nb.set_show_border(False)

		home_view = HomeView(shell)
		self._nb.append_page(home_view)
		self._setup_canvas(home_view)
		home_view.show()
		
		mesh_view = MeshView(shell)
		self._setup_canvas(mesh_view)
		self._nb.append_page(mesh_view)
		mesh_view.show()

		self.add(self._nb)
		self._nb.show()

	def _setup_canvas(self, canvas):
		canvas.set_bounds(0, 0, 1200, 900)
		canvas.set_scale(float(800) / float(1200))
		canvas.set_size_request(800, 600)

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
