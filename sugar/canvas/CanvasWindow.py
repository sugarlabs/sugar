import gtk
import goocanvas

class CanvasWindow(gtk.Window):
	def __init__(self, model):
		gtk.Window.__init__(self)

		self._view = goocanvas.CanvasView()
		self._view.set_model(model)
		self.add(self._view)
		self._view.show()

	def get_view(self):
		return self._view
