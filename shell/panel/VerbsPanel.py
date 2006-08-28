import gtk
import goocanvas

from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from sugar import conf
from panel.Panel import Panel
import logging

class ActivityItem(IconItem):
	def __init__(self, activity, size):
		icon_name = activity.get_icon()
		if not icon_name:
			act_type = activity.get_default_type()
			raise RuntimeError("Activity %s did not have an icon!" % act_type)
		IconItem.__init__(self, icon_name=icon_name,
						  color=IconColor('white'), size=size)
		self._activity = activity

	def get_activity_id(self):
		return self._activity.get_id()

class ActivityBar(goocanvas.Group):
	def __init__(self, shell, height):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._height = height

		registry = conf.get_activity_registry()
		for activity in registry.list_activities():
			if activity.get_show_launcher():
				self.add_activity(activity)

	def add_activity(self, activity):
		# Need an icon to show up on the bar
		if not activity.get_icon():
			name = activity.get_name()
			logging.info("Activity %s did not have an icon.  Won't show it." % name)
			return

		item = ActivityItem(activity, self._height)

		icon_size = self._height
		x = (icon_size + 6) * self.get_n_children()
		item.set_property('x', x)

		self.add_child(item)

class VerbsPanel(Panel):
	def __init__(self, shell):
		Panel.__init__(self)

		self._shell = shell

		view = self.get_view()
		view.connect("item_view_created", self.__item_view_created_cb)

	def construct(self):
		Panel.construct(self)

		root = self.get_root()

		activity_bar = ActivityBar(self._shell, self.get_height())
		root.add_child(activity_bar)

	def __item_view_created_cb(self, view, item_view, item):
		if isinstance(item, ActivityItem):
			item_view.connect("button_press_event",
							  self.__activity_button_press_cb,
							  item.get_activity_id())

	def __activity_button_press_cb(self, view, target, event, activity_id):
		self._shell.start_activity(activity_id)
		self._shell.get_panel_manager().hide()
