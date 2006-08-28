import goocanvas

from panel.Panel import Panel
from sugar.canvas.IconItem import IconItem

class ZoomBar(goocanvas.Group):
	def __init__(self, height):
		goocanvas.Group.__init__(self)
		self._height = height

		self.add_zoom_level('stock-zoom-activity')
		self.add_zoom_level('stock-zoom-home')
		self.add_zoom_level('stock-zoom-friends')
		self.add_zoom_level('stock-zoom-mesh')

	def add_zoom_level(self, icon_name):
		icon = IconItem(icon_name=icon_name, size=self._height)

		icon_size = self._height
		x = (icon_size + 6) * self.get_n_children()
		icon.set_property('x', x)

		self.add_child(icon)

class TopPanel(Panel):
	def __init__(self, shell):
		Panel.__init__(self)
		self._shell = shell

	def construct(self):
		Panel.construct(self)

		zoom_bar = ZoomBar(self.get_height())
		zoom_bar.translate(self.get_border(), self.get_border())
		self.get_root().add_child(zoom_bar)
