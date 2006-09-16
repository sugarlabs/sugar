from sugar.canvas.MenuIcon import MenuIcon
from view.BuddyPopup import BuddyPopup

class BuddyIcon(MenuIcon):
	def __init__(self, shell, friend):
		MenuIcon.__init__(self, shell.get_grid(),
						  icon_name='stock-buddy',
						  color=friend.get_color(), size=96)

		self._shell = shell
		self._friend = friend

	def set_popup_distance(self, distance):
		self._popup_distance = distance

	def create_menu(self):
		menu = BuddyPopup(self._shell, self._friend)
		menu.connect('action', self._popup_action_cb)
		return menu

	def _popup_action_cb(self, popup, action):
		self._popdown()

		model = self._shell.get_model()
		if action == BuddyPopup.ACTION_REMOVE_FRIEND:
			friends = model.get_friends()
			friends.remove(buddy)

		buddy = self._friend.get_buddy()
		if buddy == None:
			return

		if action == BuddyPopup.ACTION_INVITE:
			activity = model.get_current_activity()
			activity.invite(buddy)
		elif action == BuddyPopup.ACTION_MAKE_FRIEND:
			friends = model.get_friends()
			friends.make_friend(buddy)
