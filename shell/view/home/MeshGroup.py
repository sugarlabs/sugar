import random

import goocanvas

import conf
from sugar.canvas.IconItem import IconItem
from view.home.IconLayout import IconLayout
from view.BuddyIcon import BuddyIcon
from sugar.canvas.SnowflakeLayout import SnowflakeLayout

class ActivityView(goocanvas.Group):
	def __init__(self, shell, menu_shell, model):
		goocanvas.Group.__init__(self)

		self._model = model
		self._layout = SnowflakeLayout()

		icon = IconItem(icon_name=model.get_icon_name(),
						color=model.get_color(), size=80)
		self.add_child(icon)
		self._layout.set_root(icon)

	def get_size_request(self):
		size = self._layout.get_size()
		return [size, size]

class MeshGroup(goocanvas.Group):
	def __init__(self, shell, menu_shell):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._menu_shell = menu_shell
		self._model = shell.get_model().get_mesh()
		self._layout = IconLayout(shell.get_grid())
		self._buddies = {}
		self._activities = {}

		for buddy_model in self._model.get_buddies():
			self._add_buddy(buddy_model)

		self._model.connect('buddy-added', self._buddy_added_cb)
		self._model.connect('buddy-removed', self._buddy_removed_cb)

		for activity_model in self._model.get_activities():
			self._add_activity(activity_model)

		self._model.connect('activity-added', self._activity_added_cb)
		self._model.connect('activity-removed', self._activity_removed_cb)

	def _buddy_added_cb(self, model, buddy_model):
		self._add_buddy(buddy_model)

	def _buddy_removed_cb(self, model, buddy_model):
		self._remove_buddy(buddy_model) 

	def _activity_added_cb(self, model, activity_model):
		self._add_activity(activity_model)

	def _activity_removed_cb(self, model, activity_model):
		self._remove_activity(activity_model) 

	def _add_buddy(self, buddy_model):
		icon = BuddyIcon(self._shell, self._menu_shell, buddy_model)
		icon.props.size = 80
		self.add_child(icon)

		self._buddies[buddy_model.get_name()] = icon
		self._layout.add_icon(icon)

	def _remove_buddy(self, buddy_model):
		icon = self._buddies[buddy_model.get_name()]
		self.remove_child(icon)
		del self._buddies[buddy_model.get_name()]

	def _add_activity(self, activity_model):
		icon = ActivityView(self._shell, self._menu_shell, activity_model)
		self.add_child(icon)

		self._activities[activity_model.get_id()] = icon
		self._layout.add_icon(icon)

	def _remove_activity(self, activity_model):
		icon = self._activities[activity_model.get_id()]
		self.remove_child(icon)
		del self._activities[activity_model.get_id()]
