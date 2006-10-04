import hippo

from view.home.activitiesdonut import ActivitiesDonut

class HomeBox(hippo.CanvasBox):
	def __init__(self, shell):
		hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff,
								 yalign=2)

		donut = ActivitiesDonut(shell, box_width=300, box_height=300)
		self.append(donut)
