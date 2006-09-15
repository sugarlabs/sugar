import gtk
import goocanvas
import logging

import conf
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from sugar.presence import PresenceService
from sugar.canvas.CanvasBox import CanvasBox

class ActivityItem(IconItem):
	def __init__(self, activity):
		icon_name = activity.get_icon()
		IconItem.__init__(self, icon_name=icon_name, color=IconColor('white'))
		self._activity = activity

	def get_bundle_id(self):
		return self._activity.get_id()

class InviteItem(IconItem):
	def __init__(self, invite):
		IconItem.__init__(self, icon_name=invite.get_icon(),
						  color=invite.get_color())
		self._invite = invite

	def get_activity_id(self):
		return self._invite.get_activity_id()

	def get_bundle_id(self):
		return self._invite.get_bundle_id()

	def get_invite(self):
		return self._invite

class BottomPanel(CanvasBox):
	def __init__(self, grid, shell_model):
		CanvasBox.__init__(self, grid, CanvasBox.HORIZONTAL, 1)

		self._shell_model = shell_model
		self._invite_to_item = {}
		self._invites = shell_model.get_invites()

		registry = conf.get_activity_registry()
		for activity in registry.list_activities():
			if activity.get_show_launcher():
				self.add_activity(activity)

		for invite in self._invites:
			self.add_invite(invite)
		self._invites.connect('invite-added', self.__invite_added_cb)
		self._invites.connect('invite-removed', self.__invite_removed_cb)

	def __activity_clicked_cb(self, icon):
		self._shell_model.start_activity(icon.get_bundle_id())

	def __invite_clicked_cb(self, icon):
		self._invites.remove_invite(icon.get_invite())
		self._shell_model.join_activity(icon.get_bundle_id(),
								  		icon.get_activity_id())
	
	def __invite_added_cb(self, invites, invite):
		self.add_invite(invite)

	def __invite_removed_cb(self, invites, invite):
		self.remove_invite(invite)

	def add_activity(self, activity):
		item = ActivityItem(activity)
		item.connect('clicked', self.__activity_clicked_cb)
		self.set_constraints(item, 3, 3)
		self.add_child(item)

	def add_invite(self, invite):
		item = InviteItem(invite)
		item.connect('clicked', self.__invite_clicked_cb)
		self.set_constraints(item, 3, 3)
		self.add_child(item, 0)

		self._invite_to_item[invite] = item

	def remove_invite(self, invite):
		self.remove_child(self._invite_to_item[invite])
		del self._invite_to_item[invite]
