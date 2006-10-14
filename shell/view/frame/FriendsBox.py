# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import hippo

from sugar.graphics.canvasicon import CanvasIcon
from sugar.graphics.iconcolor import IconColor
from sugar.graphics import style
from sugar.presence import PresenceService
from view.BuddyIcon import BuddyIcon
from model.BuddyModel import BuddyModel
from view.frame.MenuStrategy import MenuStrategy

class FriendsBox(hippo.CanvasBox):
	def __init__(self, shell, menu_shell):
		hippo.CanvasBox.__init__(self)
		self._shell = shell
		self._menu_shell = menu_shell
		self._activity_ps = None
		self._joined_hid = -1
		self._left_hid = -1
		self._buddies = {}

		self._pservice = PresenceService.get_instance()
		self._pservice.connect('activity-appeared',
							   self.__activity_appeared_cb)

		shell.connect('activity-changed', self.__activity_changed_cb)

	def add(self, buddy):
		model = BuddyModel(buddy=buddy)
		icon = BuddyIcon(self._shell, self._menu_shell, model)
		style.apply_stylesheet(icon, 'frame.BuddyIcon')
		icon.set_menu_strategy(MenuStrategy())
		self.append(icon)

		self._buddies[buddy.get_name()] = icon

	def remove(self, buddy):
		self.remove(self._buddies[buddy.get_name()])

	def clear(self):
		for item in self.get_children():
			self.remove(item)
		self._buddies = {}

	def __activity_appeared_cb(self, pservice, activity_ps):
		activity = self._shell.get_current_activity()
		if activity and activity_ps.get_id() == activity.get_id():
			self._set_activity_ps(activity_ps)

	def _set_activity_ps(self, activity_ps):
		if self._activity_ps == activity_ps:
			return

		if self._joined_hid > 0:
			self._activity_ps.disconnect(self._joined_hid)
			self._joined_hid = -1
		if self._left_hid > 0:
			self._activity_ps.disconnect(self._left_hid)
			self._left_hid = -1

		self._activity_ps = activity_ps

		self.clear()

		if activity_ps != None:
			for buddy in activity_ps.get_joined_buddies():
				self.add(buddy)

			self._joined_hid = activity_ps.connect(
							'buddy-joined', self.__buddy_joined_cb)
			self._left_hid = activity_ps.connect(
							'buddy-left', self.__buddy_left_cb)

	def __activity_changed_cb(self, group, activity):
		if activity:
			ps = self._pservice.get_activity(activity.get_id())
			self._set_activity_ps(ps)
		else:
			self._set_activity_ps(None)

	def __buddy_joined_cb(self, activity, buddy):
		self.add(buddy)

	def __buddy_left_cb(self, activity, buddy):
		self.remove(buddy)
