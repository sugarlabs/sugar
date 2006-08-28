import gtk
import goocanvas

class PanelView(goocanvas.CanvasView):
	BORDER = 4

	def construct(self, x, y):
		model = goocanvas.CanvasModelSimple()
		root = model.get_root_item()

		item = goocanvas.Rect(x=0, y=0,
							  width=self.get_allocation().width,
							  height=self.get_allocation().height,
							  line_width=0, fill_color="#4f4f4f")
		root.add_child(item)

		self._group = goocanvas.Group()
		root.add_child(self._group)
		self._group.translate(x + PanelView.BORDER, y + PanelView.BORDER)

		self.set_model(model)

	def get_root_group(self):
		return self._group

class Panel(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)
		self._x = 0
		self._y = 0

		self._view = PanelView()
		self.add(self._view)
		self._view.show()

		self.set_decorated(False)

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

		screen = gtk.gdk.screen_get_default()
		self.window.set_transient_for(screen.get_root_window())

	def get_view(self):
		return self._view

	def get_root(self):
		return self._view.get_root_group()

	def get_height(self):
		height = self._view.get_allocation().height
		return height - PanelView.BORDER * 2

	def get_width(self):
		width = self._view.get_allocation().width
		return width - PanelView.BORDER * 2

	def set_position(self, x, y):
		self._x = x
		self._y = y

	def construct(self):
		self._view.construct(self._x, self._y)

	def show(self):
		gtk.Window.show(self)
		self.construct()
