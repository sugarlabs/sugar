import gtk
import goocanvas

from sugar.canvas.IconItem import IconItem

class Model(goocanvas.CanvasModelSimple):
	def __init__(self):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		item = goocanvas.Rect(x=0, y=0, width=1200, height=900,
							  fill_color="red")
		root.add_child(item)

		item = IconItem('buddy')
		item.set_color('blue')
		root.add_child(item)

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)

		self._shell = shell

		self.connect('realize', self.__realize_cb)

		canvas = goocanvas.CanvasView()
		canvas_model = Model()
		canvas.set_bounds(0, 0, 1200, 900)
		canvas.set_scale(float(800) / float(1200))
		canvas.set_size_request(800, 600)
		self.add(canvas)
		canvas.show()

		canvas.set_model(canvas_model)

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
