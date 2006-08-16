import gtk
import goocanvas

from sugar.canvas.IconItem import IconItem

class Model(goocanvas.CanvasModelSimple):
	def __init__(self):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		item = goocanvas.Rect(x=0, y=0, width=693, height=520,
							  fill_color="red")
		root.add_child(item)

		item = IconItem('buddy')
		#item.set_color('blue')
		root.add_child(item)

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)

		self._shell = shell

		self.connect('realize', self.__realize_cb)

		canvas = goocanvas.CanvasView()
		canvas_model = Model()
		canvas.set_bounds(0, 0, 693, 520)
		self.add(canvas)
		canvas.show()

		canvas.set_model(canvas_model)
		canvas.set_size_request(693, 520)

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
