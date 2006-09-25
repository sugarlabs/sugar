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

		self._shell = shell
		self._model = model
		self._layout = SnowflakeLayout()
		self._icons = {}

		icon = IconItem(icon_name=model.get_icon_name(),
						color=model.get_color(), size=80)
		icon.connect('clicked', self._clicked_cb)
		self.add_child(icon)
		self._layout.set_root(icon)

	def has_buddy_icon(self, name):
		return self._icons.has_key(name)

	def add_buddy_icon(self, name, icon):
		self._icons[name] = icon
		self.add_child(icon)
		self._layout.add_child(icon)

	def remove_buddy_icon(self, name):
		icon = self._icons[name]
		self._layout.remove_child(icon)
		self.remove_child(icon)
		del self._icons[name]

	def get_size_request(self):
		size = self._layout.get_size()
		return [size, size]

	def _clicked_cb(self, item):
		registry = conf.get_activity_registry()
		default_type = self._model.get_service().get_type()
		bundle = registry.get_activity_from_type(default_type)
		self._shell.join_activity(bundle.get_id(), self._model.get_id())


class MeshGroup(goocanvas.Group):
	def __init__(self, shell, menu_shell):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._menu_shell = menu_shell
		self._model = shell.get_model().get_mesh()
		self._layout = IconLayout(shell.get_grid())
		self._buddies = {}
		self._activities = {}
		self._buddy_to_activity = {}

		for buddy_model in self._model.get_buddies():
			self._add_buddy(buddy_model)

		self._model.connect('buddy-added', self._buddy_added_cb)
		self._model.connect('buddy-removed', self._buddy_removed_cb)
		self._model.connect('buddy-moved', self._buddy_moved_cb)

		for activity_model in self._model.get_activities():
			self._add_activity(activity_model)

		self._model.connect('activity-added', self._activity_added_cb)
		self._model.connect('activity-removed', self._activity_removed_cb)

	def _buddy_added_cb(self, model, buddy_model):
		self._add_alone_buddy(buddy_model)

	def _buddy_removed_cb(self, model, buddy_model):
		self._remove_buddy(buddy_model) 

	def _buddy_moved_cb(self, model, buddy_model, activity_model):
		self._move_buddy(buddy_model, activity_model)

	def _activity_added_cb(self, model, activity_model):
		self._add_activity(activity_model)

	def _activity_removed_cb(self, model, activity_model):
		self._remove_activity(activity_model) 

	def _add_alone_buddy(self, buddy_model):
		icon = BuddyIcon(self._shell, self._menu_shell, buddy_model)
		icon.props.size = 80
		self.add_child(icon)

		self._buddies[buddy_model.get_name()] = icon
		self._layout.add_icon(icon)

	def _remove_alone_buddy(self, buddy_model):
		icon = self._buddies[buddy_model.get_name()]
		self.remove_child(icon)
		self._layout.remove_icon(icon)
		del self._buddies[buddy_model.get_name()]

	def _remove_buddy(self, buddy_model):
		name = buddy_model.get_name()
		if self._buddies.has_key(name):
			self._remove_alone_buddy(buddy_model)
		else:
			for activity in self._activities.values():
				if activity.has_buddy_icon(name):
					activity.remove_buddy_icon(name)
					self._layout.update()

	def _move_buddy(self, buddy_model, activity_model):
		name = buddy_model.get_name()

		self._remove_buddy(buddy_model)

		if activity_model == None:
			self._add_alone_buddy(buddy_model)
		else:
			activity = self._activities[activity_model.get_id()]

			icon = BuddyIcon(self._shell, self._menu_shell, buddy_model)
			icon.props.size = 60
			activity.add_buddy_icon(buddy_model.get_name(), icon)

			self._layout.update()

	def _add_activity(self, activity_model):
		icon = ActivityView(self._shell, self._menu_shell, activity_model)
		self.add_child(icon)

		self._activities[activity_model.get_id()] = icon
		self._layout.add_icon(icon)

	def _remove_activity(self, activity_model):
		icon = self._activities[activity_model.get_id()]
		self.remove_child(icon)
		self._layout.remove_icon(icon)
		del self._activities[activity_model.get_id()]
