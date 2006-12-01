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
import logging

from sugar.graphics.canvasicon import CanvasIcon
from sugar.presence import PresenceService
from sugar.graphics import style

class ActivityItem(CanvasIcon):
	def __init__(self, activity):
		icon_name = activity.get_icon()
		CanvasIcon.__init__(self, icon_name=icon_name)
		style.apply_stylesheet(self, 'frame.ActivityIcon')
		self._activity = activity

	def get_bundle_id(self):
		return self._activity.get_id()

class InviteItem(CanvasIcon):
	def __init__(self, invite):
		CanvasIcon.__init__(self, icon_name=invite.get_icon())

		style.apply_stylesheet(self, 'frame.ActivityIcon')
		self.props.color = invite.get_color()

		self._invite = invite

	def get_activity_id(self):
		return self._invite.get_activity_id()

	def get_bundle_id(self):
		return self._invite.get_bundle_id()

	def get_invite(self):
		return self._invite

class ActivitiesBox(hippo.CanvasBox):
	def __init__(self, shell):
		hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

		self._shell = shell
		self._shell_model = self._shell.get_model() 
		self._invite_to_item = {}
		self._invites = self._shell_model.get_invites()

		for bundle in self._shell_model.get_bundle_registry():
			if bundle.get_show_launcher():
				self.add_activity(bundle)

		for invite in self._invites:
			self.add_invite(invite)
		self._invites.connect('invite-added', self._invite_added_cb)
		self._invites.connect('invite-removed', self._invite_removed_cb)

	def _activity_clicked_cb(self, icon):
		self._shell.start_activity(icon.get_bundle_id())

	def _invite_clicked_cb(self, icon):
		self._invites.remove_invite(icon.get_invite())
		self._shell.join_activity(icon.get_bundle_id(),
								  icon.get_activity_id())
	
	def _invite_added_cb(self, invites, invite):
		self.add_invite(invite)

	def _invite_removed_cb(self, invites, invite):
		self.remove_invite(invite)

	def add_activity(self, activity):
		item = ActivityItem(activity)
		item.connect('activated', self._activity_clicked_cb)
		self.append(item, 0)

	def add_invite(self, invite):
		item = InviteItem(invite)
		item.connect('activated', self._invite_clicked_cb)
		self.append(item, 0)

		self._invite_to_item[invite] = item

	def remove_invite(self, invite):
		self.remove(self._invite_to_item[invite])
		del self._invite_to_item[invite]
