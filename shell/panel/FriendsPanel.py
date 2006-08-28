import goocanvas

from panel.Panel import Panel
from sugar.canvas.IconItem import IconItem

class ActionsBar(goocanvas.Group):
	def __init__(self, shell, width):
		goocanvas.Group.__init__(self)
		self._width = width
		self._shell = shell

		self._y = 0

		icon = IconItem(icon_name='stock-share', size=self._width)
		icon.connect('clicked', self.__share_clicked_cb)
		self.add_icon(icon)

		icon = IconItem(icon_name='stock-invite', size=self._width)
		icon.connect('clicked', self.__invite_clicked_cb)
		self.add_icon(icon)

		icon = IconItem(icon_name='stock-chat', size=self._width)
		icon.connect('clicked', self.__chat_clicked_cb)
		self.add_icon(icon)

	def add_icon(self, icon):
		icon.set_property('y', self._y)
		self._y += (self._width + 6)
		self.add_child(icon)		

	def __share_clicked_cb(self, item):
		activity = self._shell.get_current_activity()
		if activity != None:
			activity.share()

	def __invite_clicked_cb(self, item):
		pass

	def __chat_clicked_cb(self, item):
		pass

class FriendsPanel(Panel):
	def __init__(self, shell):
		Panel.__init__(self)
		self._shell = shell

	def construct(self):
		Panel.construct(self)

		actions_bar = ActionsBar(self._shell, self.get_width())
		self.get_root().add_child(actions_bar)
