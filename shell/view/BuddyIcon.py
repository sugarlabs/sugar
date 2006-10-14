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

from sugar.graphics.menuicon import MenuIcon
from view.BuddyMenu import BuddyMenu

class BuddyIcon(MenuIcon):
	def __init__(self, shell, menu_shell, buddy):
		MenuIcon.__init__(self, menu_shell, icon_name='stock-buddy',
						  color=buddy.get_color())

		self._shell = shell
		self._buddy = buddy
		self._buddy.connect('appeared', self._buddy_presence_change_cb)
		self._buddy.connect('disappeared', self._buddy_presence_change_cb)
		self._buddy.connect('color-changed', self._buddy_presence_change_cb)

	def _buddy_presence_change_cb(self, buddy, color=None):
		# Update the icon's color when the buddy comes and goes
		self.set_property('color', buddy.get_color())

	def set_popup_distance(self, distance):
		self._popup_distance = distance

	def create_menu(self):
		menu = BuddyMenu(self._shell, self._buddy)
		menu.connect('action', self._popup_action_cb)
		return menu

	def _popup_action_cb(self, popup, action):
		self.popdown()

		friends = self._shell.get_model().get_friends()
		if action == BuddyMenu.ACTION_REMOVE_FRIEND:
			friends.remove(self._buddy)

		ps_buddy = self._buddy.get_buddy()
		if ps_buddy == None:
			return

		if action == BuddyMenu.ACTION_INVITE:
			activity = self._shell.get_current_activity()
			activity.invite(ps_buddy)
		elif action == BuddyMenu.ACTION_MAKE_FRIEND:
			friends.make_friend(ps_buddy)
