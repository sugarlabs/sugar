import gtk
import goocanvas
import wnck

from sugar.canvas.IconItem import IconItem
from sugar.canvas.DonutItem import DonutItem
from sugar.canvas.DonutItem import PieceItem

class TasksItem(DonutItem):
	def __init__(self, shell):
		DonutItem.__init__(self, 250)

		self._items = {}

		shell.connect('activity_opened', self.__activity_opened_cb)
		shell.connect('activity_closed', self.__activity_closed_cb)

	def __activity_opened_cb(self, shell, activity):
		self._add(activity)

	def __activity_closed_cb(self, shell, activity):
		self._remove(activity)
	
	def _remove(self, activity):
		item = self._items[activity.get_id()]
		self.remove_child(item)
		del self._items[activity.get_id()]

	def _add(self, activity):
		icon_name = activity.get_icon_name()
		item = self.add_piece(100 / 8, icon_name, 'blue')
		item.set_data('activity', activity)
		self._items[activity.get_id()] = item

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

		tasks = TasksItem(shell)
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
		elif isinstance(item, PieceItem):
			item_view.connect("button_press_event",
							  self.__task_button_press_cb)

	def __activity_button_press_cb(self, view, target, event, activity_id):
		self._shell.start_activity(activity_id)

	def __task_button_press_cb(self, view, target, event):
		activity = view.get_item().get_data('activity')
		activity.present()

	def __realize_cb(self, window):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
