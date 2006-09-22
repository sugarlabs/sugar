from sugar.canvas.MenuIcon import MenuIcon
from view.BuddyMenu import BuddyMenu

class BuddyIcon(MenuIcon):
	def __init__(self, shell, menu_shell, friend):
		MenuIcon.__init__(self, menu_shell, icon_name='stock-buddy',
						  color=friend.get_color(), size=112)

		self._shell = shell
		self._friend = friend

	def set_popup_distance(self, distance):
		self._popup_distance = distance

	def create_menu(self):
		menu = BuddyMenu(self._shell, self._friend)
		menu.connect('action', self._popup_action_cb)
		return menu

	def _popup_action_cb(self, popup, action):
		self.popdown()

		friends = self._shell.get_model().get_friends()
		if action == BuddyMenu.ACTION_REMOVE_FRIEND:
			friends.remove(self._friend)

		buddy = self._friend.get_buddy()
		if buddy == None:
			return

		if action == BuddyMenu.ACTION_INVITE:
			activity = self._shell.get_current_activity()
			activity.invite(buddy)
		elif action == BuddyMenu.ACTION_MAKE_FRIEND:
			friends.make_friend(buddy)
