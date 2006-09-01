import gtk
import gobject

from frame.BottomPanel import BottomPanel
from frame.RightPanel import RightPanel
from frame.TopPanel import TopPanel
from frame.Panel import Panel

class Frame:
	def __init__(self, shell, owner):
		size = 30

		self._panels = []

		panel = BottomPanel(shell)
		panel.set_position(size, 0)
		panel.move(0, gtk.gdk.screen_height() - size)
		panel.resize(gtk.gdk.screen_width(), size)
		self._panels.append(panel)

		panel = RightPanel(shell, owner.get_friends())
		panel.move(gtk.gdk.screen_width() - size, size)
		panel.resize(size, gtk.gdk.screen_height() - size * 2)
		self._panels.append(panel)

		panel = TopPanel(shell)
		panel.set_position(size, 0)
		panel.move(0, 0)
		panel.resize(gtk.gdk.screen_width(), size)
		self._panels.append(panel)

		panel = Panel()
		panel.move(0, size)
		panel.resize(size, gtk.gdk.screen_height() - size * 2)
		self._panels.append(panel)

	def __hide_timeout_cb(self):
		self.hide()
		return False

	def show_and_hide(self, seconds):
		self.show()
		gobject.timeout_add(seconds * 1000, self.__hide_timeout_cb)

	def show(self):
		for panel in self._panels:
			panel.show()

	def hide(self):
		for panel in self._panels:
			panel.hide()

	def toggle_visibility(self):
		for panel in self._panels:
			if panel.props.visible:
				panel.hide()
			else:
				panel.show()
