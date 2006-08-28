import goocanvas

from panel.Panel import Panel
from sugar.canvas.IconItem import IconItem
import sugar

class ZoomBar(goocanvas.Group):
	def __init__(self, shell, height):
		goocanvas.Group.__init__(self)
		self._height = height
		self._shell = shell

		self.add_zoom_level(sugar.ZOOM_ACTIVITY, 'stock-zoom-activity')
		self.add_zoom_level(sugar.ZOOM_HOME, 'stock-zoom-home')
		self.add_zoom_level(sugar.ZOOM_FRIENDS, 'stock-zoom-friends')
		self.add_zoom_level(sugar.ZOOM_MESH, 'stock-zoom-mesh')

	def add_zoom_level(self, level, icon_name):
		icon = IconItem(icon_name=icon_name, size=self._height)
		icon.connect('clicked', self.__level_clicked_cb, level)

		icon_size = self._height
		x = (icon_size + 6) * self.get_n_children()
		icon.set_property('x', x)

		self.add_child(icon)

	def __level_clicked_cb(self, item, level):
		self._shell.set_zoom_level(level)

class TopPanel(Panel):
	def __init__(self, shell):
		Panel.__init__(self)
		self._shell = shell

	def construct(self):
		Panel.construct(self)

		zoom_bar = ZoomBar(self._shell, self.get_height())
		self.get_root().add_child(zoom_bar)
