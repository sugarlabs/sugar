import gtk
import goocanvas
import cairo

from sugar.canvas.CanvasView import CanvasView
from home.MeshGroup import MeshGroup
from home.HomeGroup import HomeGroup
from home.FriendsGroup import FriendsGroup
from home.IconLayout import IconLayout
import sugar

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)
		self._shell = shell

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)

		view = CanvasView()
		self.add(view)
		view.show()

		model = goocanvas.CanvasModelSimple()
		self._root = model.get_root_item()
		view.set_model(model)

		bg = goocanvas.Rect(width=1900, height=1200,
							line_width=0, fill_color='#e2e2e2')
		self._root.add_child(bg)

		self._home_group = HomeGroup(self._shell)
		self._root.add_child(self._home_group)
		self._current_group = self._home_group

	def set_owner(self, owner):
		layout = IconLayout(1900, 1200)
		friends = owner.get_friends()
		self._friends_group = FriendsGroup(self._shell, friends, layout)

		layout = IconLayout(1900, 1200)
		self._mesh_group = MeshGroup(self._shell, layout)

	def _set_group(self, group):
		self._root.remove_child(self._current_group)
		self._root.add_child(group)
		self._current_group = group

	def set_zoom_level(self, level):
		if level == sugar.ZOOM_HOME:
			self._set_group(self._home_group)
		elif level == sugar.ZOOM_FRIENDS:
			self._set_group(self._friends_group)
		elif level == sugar.ZOOM_MESH:
			self._set_group(self._mesh_group)
