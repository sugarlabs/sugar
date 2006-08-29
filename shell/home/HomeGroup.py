import gtk
import goocanvas
import wnck

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from home.DonutItem import DonutItem
from home.DonutItem import PieceItem
from home.DonutItem import PieceIcon
import sugar.conf

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
		icon_color = activity.get_icon_color()
		item = self.add_piece(100 / 8, icon_name, icon_color)

		# FIXME This really sucks. Fix goocanvas event handling.
		item.set_data('activity', activity)
		item.get_icon().set_data('activity', activity)

		self._items[activity.get_id()] = item

class Background(goocanvas.Group):
	def __init__(self):
		goocanvas.Group.__init__(self)

class HomeGroup(goocanvas.Group):
	WIDTH = 1200.0
	HEIGHT = 900.0

	def __init__(self, shell):
		goocanvas.Group.__init__(self)

		self._theme = Theme.get_instance()
		self._theme.connect("theme-changed", self.__theme_changed_cb)

		color = self._theme.get_home_activities_color()
		self._home_rect = goocanvas.Rect(width=HomeGroup.WIDTH,
										 height=HomeGroup.HEIGHT,
										 line_width=0, fill_color=color,
										 radius_x=30, radius_y=30)
		self.add_child(self._home_rect)

		tasks = TasksItem(shell)
		tasks.translate(600, 450)
		self.add_child(tasks)

		profile = sugar.conf.get_profile()
		me = IconItem(icon_name = 'stock-buddy',
					  color = profile.get_color(), size = 150)
		me.translate(600 - (me.get_property('width') / 2),
					 450 - (me.get_property('height') / 2))
		self.add_child(me)

	def get_width(self):
		return 1200.0 * 1.8

	def get_height(self):
		return 900.0 * 1.8

	def __theme_changed_cb(self, theme):
		color = self._theme.get_home_activities_color()
		self._home_rect.set_property("fill-color", color)


#	def __item_view_created_cb(self, view, item_view, item):
#		if isinstance(item, PieceItem) or \
#		   isinstance(item, PieceIcon):
#			item_view.connect("button_press_event",
#							  self.__task_button_press_cb)
#
#	def __activity_button_press_cb(self, view, target, event, activity_id):
#		self._shell.start_activity(activity_id)
#
#	def __task_button_press_cb(self, view, target, event):
#		activity = view.get_item().get_data('activity')
#		activity.present()
