import gtk
import goocanvas

from sugar.canvas.IconItem import IconItem

class ActivityBar(goocanvas.Group):
	def __init__(self, registry):
		goocanvas.Group.__init__(self)

		for activity in registry.list_activities():
			if activity.get_show_launcher():
				self.add_activity(activity)

	def add_activity(self, activity):
		item = IconItem(icon_name=activity.get_icon(),
						color='white', width=42, height=42)
		self.add_child(item)

class Background(goocanvas.Group):
	def __init__(self):
		goocanvas.Group.__init__(self)

		item = goocanvas.Rect(width=1200, height=900,
							  fill_color="#4f4f4f")
		self.add_child(item)

		item = goocanvas.Rect(x=50, y=50, width=1100, height=800,
							  line_width=0, fill_color="#d8d8d8",
							  radius_x=30, radius_y=30)
		self.add_child(item)

		item = goocanvas.Text(text="My Activities",
							  x=60, y=10, fill_color="white",
                              font="Sans 21")
		self.add_child(item)

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, shell):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		background = Background()
		root.add_child(background)

		activity_bar = ActivityBar(shell.get_registry())
		root.add_child(activity_bar)

class HomeWindow(gtk.Window):
	def __init__(self, shell):
		gtk.Window.__init__(self)

		self._shell = shell

		self.connect('realize', self.__realize_cb)

		canvas = goocanvas.CanvasView()
		canvas_model = Model(shell)
		canvas.set_bounds(0, 0, 1200, 900)
		canvas.set_scale(float(800) / float(1200))
		canvas.set_size_request(800, 600)
		self.add(canvas)
		canvas.show()

		canvas.set_model(canvas_model)

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
