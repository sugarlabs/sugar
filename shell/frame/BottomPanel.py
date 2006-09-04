import gtk
import goocanvas
import logging

import conf
from sugar.canvas.IconItem import IconItem
from sugar.canvas.IconColor import IconColor
from sugar.presence import PresenceService
from frame.Panel import Panel

class ActivityItem(IconItem):
	def __init__(self, activity, size):
		icon_name = activity.get_icon()
		if not icon_name:
			act_type = activity.get_type()
			raise RuntimeError("Activity %s did not have an icon!" % act_type)
		IconItem.__init__(self, icon_name=icon_name,
						  color=IconColor('white'), size=size)
		self._activity = activity

	def get_bundle_id(self):
		return self._activity.get_id()

class InviteItem(IconItem):
	def __init__(self, invite, size):
		IconItem.__init__(self, icon_name=invite.get_icon(),
						  color=invite.get_color(), size=size)
		self._invite = invite

	def get_activity_id(self):
		return self._invite.get_activity_id()

	def get_bundle_id(self):
		return self._invite.get_bundle_id()

class ActivityBar(goocanvas.Group):
	def __init__(self, shell, invites, height):
		goocanvas.Group.__init__(self)

		self._shell = shell
		self._height = height

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

		item = ActivityItem(activity, self._height)
		item.connect('clicked', self.__activity_clicked_cb)

		icon_size = self._height
		x = (icon_size + 6) * self.get_n_children()
		item.set_property('x', x)

		self.add_child(item)

	def add_invite(self, invite):
		item = InviteItem(invite, self._height)
		item.connect('clicked', self.__invite_clicked_cb)

		icon_size = self._height
		x = (icon_size + 6) * self.get_n_children()
		item.set_property('x', x)

		self.add_child(item)

class BottomPanel(Panel):
	def __init__(self, shell, invites):
		Panel.__init__(self)

		self._shell = shell
		self._invites = invites

	def construct(self):
		Panel.construct(self)

		root = self.get_root()

		activity_bar = ActivityBar(self._shell, self._invites,
								   self.get_height())
		root.add_child(activity_bar)
