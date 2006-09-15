import goocanvas

from sugar.canvas.CanvasBox import CanvasBox
from sugar.canvas.IconItem import IconItem
import sugar

class TopPanel(goocanvas.Group):
	def __init__(self, shell):
		goocanvas.Group.__init__(self)

		self._shell = shell

		grid = shell.get_grid()

		box = CanvasBox(grid, CanvasBox.HORIZONTAL, 1)
		grid.set_constraints(box, 5, 0)
		self.add_child(box)

		icon = IconItem(icon_name='stock-zoom-activity')
		icon.connect('clicked', self.__level_clicked_cb, sugar.ZOOM_ACTIVITY)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-zoom-home')
		icon.connect('clicked', self.__level_clicked_cb, sugar.ZOOM_HOME)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-zoom-friends')
		icon.connect('clicked', self.__level_clicked_cb, sugar.ZOOM_FRIENDS)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-zoom-mesh')
		icon.connect('clicked', self.__level_clicked_cb, sugar.ZOOM_MESH)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		box = CanvasBox(grid, CanvasBox.HORIZONTAL, 1)
		grid.set_constraints(box, 60, 0)
		self.add_child(box)

		icon = IconItem(icon_name='stock-share')
		icon.connect('clicked', self.__share_clicked_cb)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-invite')
		icon.connect('clicked', self.__invite_clicked_cb)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

		icon = IconItem(icon_name='stock-chat')
		icon.connect('clicked', self.__chat_clicked_cb)
		box.set_constraints(icon, 3, 3)
		box.add_child(icon)

	def __level_clicked_cb(self, item, level):
		self._shell.set_zoom_level(level)

	def __share_clicked_cb(self, item):
		shell_model = self._shell.get_model()
		activity = shell_model.get_current_activity()
		if activity != None:
			activity.share()

	def __invite_clicked_cb(self, item):
		pass

	def __chat_clicked_cb(self, item):
		pass
