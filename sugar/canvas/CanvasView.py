import gtk
import goocanvas

class CanvasView(goocanvas.CanvasView):
	def __init__(self):
		goocanvas.CanvasView.__init__(self)

		self.set_size_request(gtk.gdk.screen_width(),
							  gtk.gdk.screen_height())
		self.set_bounds(0, 0, 1200, 900)
		self.set_scale(gtk.gdk.screen_width() / 1200.0)
