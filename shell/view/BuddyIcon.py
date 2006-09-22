from sugar.canvas.MenuIcon import MenuIcon
from view.BuddyMenu import BuddyMenu

class BuddyIcon(MenuIcon):
	def __init__(self, shell, menu_shell, buddy):
		MenuIcon.__init__(self, menu_shell, icon_name='stock-buddy',
						  color=buddy.get_color(), size=112)

		self._shell = shell
		self._buddy = buddy
		self._buddy.connect('appeared', self.__buddy_presence_change_cb)
		self._buddy.connect('disappeared', self.__buddy_presence_change_cb)
		self._buddy.connect('color-changed', self.__buddy_presence_change_cb)

	def __buddy_presence_change_cb(self, buddy, color=None):
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
