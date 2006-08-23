import gtk
import goocanvas
import wnck

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor
from sugar.canvas.DonutItem import DonutItem
from sugar.canvas.DonutItem import PieceItem
from sugar.canvas.DonutItem import PieceIcon

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
		self.remove_piece(item)
		del self._items[activity.get_id()]

	def _add(self, activity):
		icon_name = activity.get_icon_name()
		item = self.add_piece(100 / 8, icon_name, IconColor())

		# FIXME This really sucks. Fix goocanvas event handling.
		item.set_data('activity', activity)
		item.get_icon().set_data('activity', activity)

		self._items[activity.get_id()] = item

class Background(goocanvas.Group):
	def __init__(self):
		goocanvas.Group.__init__(self)

		item = goocanvas.Rect(width=1200, height=900,
							  fill_color="#d8d8d8")
		self.add_child(item)

		item = goocanvas.Text(text="My Activities",
							  x=12, y=12, fill_color="black",
                              font="Sans 21")
		self.add_child(item)

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, shell):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		background = Background()
		root.add_child(background)

		tasks = TasksItem(shell)
		tasks.translate(600, 450)
		root.add_child(tasks)

		me = IconItem('stock-buddy', IconColor(), 150)
		me.translate(600 - (me.get_property('width') / 2),
					 450 - (me.get_property('height') / 2))
		root.add_child(me)

class HomeView(goocanvas.CanvasView):
	def __init__(self, shell):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(shell)
		self.set_model(canvas_model)

	def __item_view_created_cb(self, view, item_view, item):
		if isinstance(item, PieceItem) or \
		   isinstance(item, PieceIcon):
			item_view.connect("button_press_event",
							  self.__task_button_press_cb)

	def __activity_button_press_cb(self, view, target, event, activity_id):
		self._shell.start_activity(activity_id)

	def __task_button_press_cb(self, view, target, event):
		activity = view.get_item().get_data('activity')
		activity.present()
