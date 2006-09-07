import gtk
import goocanvas
import logging

import conf
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from sugar.presence import PresenceService
from sugar.canvas.GridLayout import GridGroup
from sugar.canvas.GridLayout import GridConstraints

class ActivityItem(IconItem):
	def __init__(self, activity):
		icon_name = activity.get_icon()
		if not icon_name:
			act_type = activity.get_type()
			raise RuntimeError("Activity %s did not have an icon!" % act_type)
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

class BottomPanel(GridGroup):
	def __init__(self, shell, invites):
		GridGroup.__init__(self, 16, 1)

		self._shell = shell

		registry = conf.get_activity_registry()
		for activity in registry.list_activities():
			if activity.get_show_launcher():
				self.add_activity(activity)

		for invite in invites:
			self.add_invite(invite)
		invites.connect('invite-added', self.__invite_added_cb)

	def __activity_clicked_cb(self, icon):
		self._shell.start_activity(icon.get_bundle_id())

	def __invite_clicked_cb(self, icon):
		self._shell.join_activity(icon.get_bundle_id(),
								  icon.get_activity_id())
	
	def __invite_added_cb(self, invites, invite):
		self.add_invite(invite)

	def add_activity(self, activity):
		# Need an icon to show up on the bar
		if not activity.get_icon():
			name = activity.get_name()
			logging.info("Activity %s did not have an icon.  Won't show it." % name)
			return

		item = ActivityItem(activity)
		item.connect('clicked', self.__activity_clicked_cb)
		constraints = GridConstraints(self.get_n_children() + 1, 0, 1, 1)
		constraints.padding = 6
		self._layout.set_constraints(item, constraints)
		self.add_child(item)

	def add_invite(self, invite):
		item = InviteItem(invite)
		item.connect('clicked', self.__invite_clicked_cb)
		self.add_child(item)
