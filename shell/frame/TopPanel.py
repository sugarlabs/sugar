import goocanvas

from sugar.canvas.GridLayout import GridGroup
from sugar.canvas.GridLayout import GridConstraints
from sugar.canvas.IconItem import IconItem
import sugar

class TopPanel(GridGroup):
	def __init__(self, shell):
		GridGroup.__init__(self, 16, 1)
		self._shell = shell

		self.add_zoom_level(sugar.ZOOM_ACTIVITY, 'stock-zoom-activity', 1)
		self.add_zoom_level(sugar.ZOOM_HOME, 'stock-zoom-home', 2)
		self.add_zoom_level(sugar.ZOOM_FRIENDS, 'stock-zoom-friends', 3)
		self.add_zoom_level(sugar.ZOOM_MESH, 'stock-zoom-mesh', 4)

		icon = IconItem(icon_name='stock-share', size=self._width)
		icon.connect('clicked', self.__share_clicked_cb)
		self.add_icon(icon, 12)

		icon = IconItem(icon_name='stock-invite', size=self._width)
		icon.connect('clicked', self.__invite_clicked_cb)
		self.add_icon(icon, 13)

		icon = IconItem(icon_name='stock-chat', size=self._width)
		icon.connect('clicked', self.__chat_clicked_cb)
		self.add_icon(icon, 14)

	def add_zoom_level(self, level, icon_name, pos):
		icon = IconItem(icon_name=icon_name, size=self._height)
		icon.connect('clicked', self.__level_clicked_cb, level)

		constraints = GridConstraints(pos, 0, 1, 1, 6)
		self._layout.set_constraints(icon, constraints)
		self.add_child(icon)

	def add_icon(self, icon, pos):
		constraints = GridConstraints(pos, 0, 1, 1, 6)
		self._layout.set_constraints(icon, constraints)
		self.add_child(icon)

	def __level_clicked_cb(self, item, level):
		self._shell.set_zoom_level(level)

	def __share_clicked_cb(self, item):
		activity = self._shell.get_current_activity()
		if activity != None:
			activity.share()

	def __invite_clicked_cb(self, item):
		pass

	def __chat_clicked_cb(self, item):
		pass
