import gtk
import hippo
import cairo

from sugar.graphics.menushell import MenuShell
from view.home.MeshBox import MeshBox
from view.home.HomeBox import HomeBox
from view.home.FriendsBox import FriendsBox
import sugar

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

		self._nb = gtk.Notebook()
		self._nb.set_show_border(False)
		self._nb.set_show_tabs(False)

		self.add(self._nb)
		self._nb.show()

		menu_shell = MenuShell()

		canvas = hippo.Canvas()
		box = HomeBox(shell)
		canvas.set_root(box)
		self._nb.append_page(canvas)
		canvas.show()

		canvas = hippo.Canvas()
		box = FriendsBox(shell, menu_shell)
		canvas.set_root(box)
		self._nb.append_page(canvas)
		canvas.show()

		canvas = hippo.Canvas()
		box = MeshBox(shell, menu_shell)
		canvas.set_root(box)
		self._nb.append_page(canvas)
		canvas.show()

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_HOME:
			self._nb.set_current_page(0)
		elif level == sugar.ZOOM_FRIENDS:
			self._nb.set_current_page(1)
		elif level == sugar.ZOOM_MESH:
			self._nb.set_current_page(2)
