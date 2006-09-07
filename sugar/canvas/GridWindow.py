import gtk
import goocanvas

class GridWindow(gtk.Window):
	def __init__(self, model):
		gtk.Window.__init__(self)

		self._model = model

		self._view = goocanvas.CanvasView()
		self._view.set_model(model.get())
		self.add(self._view)
		self._view.show()

	def scale_to_screen(self):
		self._view.set_scale(float(gtk.gdk.screen_width()) /
							 float(self._model.get_width()))

	def set_bounds(self, constraints):
		bounds = self._model.get_bounds(constraints)
		self._view.set_bounds(bounds[0], bounds[1],
							  bounds[2], bounds[3])

	def get_view(self):
		return self._view
