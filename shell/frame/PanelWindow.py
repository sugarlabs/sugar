import gtk
import goocanvas

from sugar.canvas.CanvasView import CanvasView

class PanelWindow(gtk.Window):
	def __init__(self, grid, model, x, y, width, height):
		gtk.Window.__init__(self)

		self._grid = grid

		self.set_decorated(False)

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.window.set_accept_focus(False)

		screen = gtk.gdk.screen_get_default()
		self.window.set_transient_for(screen.get_root_window())

		view = CanvasView()
		view.show()
		self.add(view)
		view.set_model(model)

		self._grid.set_constraints(self, x, y, width, height)
		self._grid.set_constraints(view, x, y, width, height)
