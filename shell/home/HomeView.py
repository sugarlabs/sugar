import gtk
import goocanvas
import wnck

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconItem import IconColor
from sugar.canvas.DonutItem import DonutItem
from sugar.canvas.DonutItem import PieceItem
from sugar.canvas.DonutItem import PieceIcon

import Theme

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
		self._theme = Theme.get_instance()
		self._theme.connect("theme-changed", self.__theme_changed_cb)

		color = self._theme.get_home_friends_color()
		self._friends_rect = goocanvas.Rect(width=1200, height=900,
										  fill_color=color)
		self.add_child(self._friends_rect)

		color = self._theme.get_home_activities_color()
		self._home_rect = goocanvas.Rect(x=100, y=100, width=1000, height=700,
										  line_width=0, fill_color=color,
										  radius_x=30, radius_y=30)
		self.add_child(self._home_rect)

		item = goocanvas.Text(text="My Activities",
							  x=12, y=12, fill_color="black",
                              font="Sans 21")
		self.add_child(item)

	def __theme_changed_cb(self, theme):
		color = self._theme.get_home_activities_color()
		self._home_rect.set_property("fill-color", color)
		color = self._theme.get_friends_colors()
		self._friends_rect.set_property("fill-color", color)

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
