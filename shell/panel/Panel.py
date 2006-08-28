import gtk
import goocanvas

class PanelModel(goocanvas.CanvasModelSimple):
	BORDER = 4

	def __init__(self, width, height):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		item = goocanvas.Rect(x=0, y=0, width=width, height=height,
							  line_width=0, fill_color="#4f4f4f")
		root.add_child(item)

class PanelView(goocanvas.CanvasView):
	def construct(self):
		canvas_model = PanelModel(self.get_allocation().width,
							      self.get_allocation().height)
		self.set_model(canvas_model)

class Panel(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		self._view = PanelView()
		self.add(self._view)
		self._view.show()

		self.connect('realize', self.__realize_cb)

	def get_view(self):
		return self._view

	def get_model(self):
		return self._view.get_model()

	def get_root(self):
		return self.get_model().get_root_item()

	def get_border(self):
		return PanelModel.BORDER

	def get_height(self):
		height = self._view.get_allocation().height
		return height - self.get_border() * 2

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DOCK)

	def construct(self):
		self._view.construct()

	def show(self):
		gtk.Window.show(self)
		self.construct()
