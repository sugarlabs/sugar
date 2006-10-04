import hippo

from view.home.activitiesdonut import ActivitiesDonut
from view.home.MyIcon import MyIcon

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarHomeBox'

	def __init__(self, shell):
		hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff,
								 yalign=2)

		donut = ActivitiesDonut(shell, box_width=300, box_height=300)
		self.append(donut)

		self._my_icon = MyIcon(120)
		self.append(self._my_icon, hippo.PACK_FIXED)

	def do_allocate(self, width, height):
		hippo.CanvasBox.do_allocate(self, width, height)

		[icon_width, icon_height] = self._my_icon.get_allocation()
		self.move(self._my_icon, (width - icon_width) / 2,
				  (height - icon_height) / 2)
