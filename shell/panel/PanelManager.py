import gtk
import gobject

from panel.VerbsPanel import VerbsPanel
from panel.FriendsPanel import FriendsPanel
from panel.TopPanel import TopPanel
from panel.Panel import Panel

class PanelManager:
	def __init__(self, shell, owner):
		size = 30

		self._verbs_panel = VerbsPanel(shell)
		self._verbs_panel.set_position(size, 0)
		self._verbs_panel.move(0, gtk.gdk.screen_height() - size)
		self._verbs_panel.resize(gtk.gdk.screen_width(), size)

		self._friends_panel = FriendsPanel(shell, owner.get_friends())
		self._friends_panel.move(gtk.gdk.screen_width() - size, size)
		self._friends_panel.resize(size, gtk.gdk.screen_height() - size * 2)

		self._top_panel = TopPanel(shell)
		self._top_panel.set_position(size, 0)
		self._top_panel.move(0, 0)
		self._top_panel.resize(gtk.gdk.screen_width(), size)

		self._left_panel = Panel()
		self._left_panel.move(0, size)
		self._left_panel.resize(size, gtk.gdk.screen_height() - size * 2)

	def __hide_timeout_cb(self):
		self.hide()
		return False

	def show_and_hide(self, seconds):
		self.show()
		gobject.timeout_add(seconds * 1000, self.__hide_timeout_cb)

	def show(self):
		self._verbs_panel.show()
		self._friends_panel.show()
		self._top_panel.show()
		self._left_panel.show()

	def hide(self):
		self._verbs_panel.hide()
		self._friends_panel.hide()
		self._top_panel.hide()
		self._left_panel.hide()

	def toggle_visibility(self):
		if self._verbs_panel.props.visible:
			self.hide()
		else:
			self.show()
