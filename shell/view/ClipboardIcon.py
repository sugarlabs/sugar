from sugar.graphics.menuicon import MenuIcon
from view.ClipboardMenu import ClipboardMenu
from sugar.activity import ActivityFactory

class ClipboardIcon(MenuIcon):
	def __init__(self, menu_shell, file_name):
		MenuIcon.__init__(self, menu_shell, icon_name='stock-written-doc')
		self._file_name = file_name
		self._percent = 0
		self.connect('activated', self._icon_activated_cb)
		self._menu = None
		
	def create_menu(self):
		self._menu = ClipboardMenu(self._file_name, self._percent)
		self._menu.connect('action', self._popup_action_cb)
		return self._menu

	def set_percent(self, percent):
		self._percent = percent
		if self._menu:
			self._menu.set_percent(percent)

	def _icon_activated_cb(self, icon):
		activity = ActivityFactory.create("org.laptop.sugar.Xbook")
		activity.execute("open_document", [self._file_name])

	def _popup_action_cb(self, popup, action):
#		self.popdown()
#		
#		if action == ClipboardMenu.ACTION_DELETE:
#			activity = self._shell.get_current_activity()
#			activity.invite(ps_buddy)
		pass
