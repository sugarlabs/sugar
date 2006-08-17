import gtk
import goocanvas
import wnck

from sugar.canvas.IconItem import IconItem
from sugar.canvas.DonutItem import DonutItem

class TasksItem(DonutItem):
	def __init__(self):
		DonutItem.__init__(self, 200)

		self._items = {}

		screen = wnck.screen_get_default()
		for window in screen.get_windows():
			if not window.is_skip_tasklist():
				self._add(window)
		screen.connect('window_opened', self.__window_opened_cb)
		screen.connect('window_closed', self.__window_closed_cb)

	def __window_opened_cb(self, screen, window):
		if not window.is_skip_tasklist():
			self._add(window)

	def __window_closed_cb(self, screen, window):
		if not window.is_skip_tasklist():
			self._remove(window)
	
	def _remove(self, window):
		item = self._items[window.get_xid()]
		self.remove_child(item)
		del self._items[window.get_xid()]

	def _add(self, window):
		item = self.add_piece(100 / 8)
		self._items[window.get_xid()] = item

class ActivityItem(IconItem):
	def __init__(self, activity):
		IconItem.__init__(self, activity.get_icon(), 'white', 30)
		self._activity = activity

	def get_activity_id(self):
		return self._activity.get_id()

class ActivityBar(goocanvas.Group):
	def __init__(self, shell):
		goocanvas.Group.__init__(self)

		self._shell = shell

		registry = shell.get_registry()
		for activity in registry.list_activities():
			if activity.get_show_launcher():
				self.add_activity(activity)

	def add_activity(self, activity):
		item = ActivityItem(activity)
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

		activity_bar = ActivityBar(shell)
		activity_bar.translate(50, 860)
		root.add_child(activity_bar)

		tasks = TasksItem()
		tasks.translate(600, 450)
		root.add_child(tasks)

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

		canvas.connect("item_view_created", self.__item_view_created_cb)

		self.add(canvas)
		canvas.show()

		canvas.set_model(canvas_model)

	def __item_view_created_cb(self, view, item_view, item):
		if isinstance(item, ActivityItem):
			item_view.connect("button_press_event",
							  self.__activity_button_press_cb,
							  item.get_activity_id())

	def __activity_button_press_cb(self, view, target, event, activity_id):
		self._shell.start_activity(activity_id)

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
