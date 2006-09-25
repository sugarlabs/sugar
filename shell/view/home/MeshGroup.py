import random

import goocanvas

import conf
from sugar.canvas.IconItem import IconItem
from view.home.IconLayout import IconLayout
from view.BuddyIcon import BuddyIcon

class MeshGroup(goocanvas.Group):
	def __init__(self, shell, menu_shell):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._menu_shell = menu_shell
		self._model = shell.get_model().get_mesh()
		self._layout = IconLayout(shell.get_grid())

		for buddy_model in self._model.get_buddies():
			self._add_buddy(buddy_model)

		self._model.connect('buddy-added', self._buddy_added_cb)

	def _buddy_added_cb(self, model, buddy_model):
		self._add_buddy(buddy_model) 

	def _add_buddy(self, buddy_model):
		icon = BuddyIcon(self._shell, self._menu_shell, buddy_model)
		self.add_child(icon)
		self._layout.add_icon(icon)
