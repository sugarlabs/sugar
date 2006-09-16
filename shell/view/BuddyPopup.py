import gtk
import goocanvas
import gobject

from sugar.canvas.Menu import Menu
from sugar.canvas.IconItem import IconItem
from sugar.presence import PresenceService

class BuddyPopup(Menu):
	ACTION_MAKE_FRIEND = 0
	ACTION_INVITE = 1
	ACTION_REMOVE_FRIEND = 2

	def __init__(self, shell, buddy):
		color = buddy.get_color()
		Menu.__init__(self, shell.get_grid(), buddy.get_name(),
					  color.get_fill_color(), color.get_stroke_color())

		self._buddy = buddy
		self._shell = shell

		owner = shell.get_model().get_owner()
		if buddy.get_name() != owner.get_name():
			self._add_actions()

	def _add_actions(self):
		shell_model = self._shell.get_model()
		pservice = PresenceService.get_instance()

		friends = shell_model.get_friends()
		if friends.has_buddy(self._buddy):
			icon = IconItem(icon_name='stock-remove-friend')
			self.add_action(icon, BuddyPopup.ACTION_REMOVE_FRIEND) 
		else:
			icon = IconItem(icon_name='stock-make-friend')
			self.add_action(icon, BuddyPopup.ACTION_MAKE_FRIEND)

		icon = IconItem(icon_name='stock-chat')
		self.add_action(icon, -1)

		activity = shell_model.get_current_activity()
		if activity != None:
			activity_ps = pservice.get_activity(activity.get_id())

			# FIXME check that the buddy is not in the activity already

			icon = IconItem(icon_name='stock-invite')
			self.add_action(icon, BuddyPopup.ACTION_INVITE)
