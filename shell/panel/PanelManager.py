import gtk

from panel.VerbsPanel import VerbsPanel
from panel.FriendsPanel import FriendsPanel
from panel.Panel import Panel

class PanelManager:
	def __init__(self, shell):
		size = 30

		self._verbs_panel = VerbsPanel(shell)
		self._verbs_panel.move(0, gtk.gdk.screen_height() - size)
		self._verbs_panel.resize(gtk.gdk.screen_width(), size)
		self._verbs_panel.show()

		self._friends_panel = FriendsPanel(shell)
		self._friends_panel.move(gtk.gdk.screen_width() - size, 0)
		self._friends_panel.resize(size, gtk.gdk.screen_height())
		self._friends_panel.show()

		panel = Panel()
		panel.move(0, 0)
		panel.resize(gtk.gdk.screen_width(), size)
		panel.show()

		panel = Panel()
		panel.move(0, 0)
		panel.resize(size, gtk.gdk.screen_height())
		panel.show()
