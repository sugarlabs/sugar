import math

from sugar.scene.LayoutManager import LayoutManager

class CircleLayout(LayoutManager):
	def __init__(self, radium):
		LayoutManager.__init__(self)

		self._radium = radium

	def layout_group(self, group):
		step = 2 * math.pi / len(group.get_actors())
		angle = 2 * math.pi
		for actor in group.get_actors():
			self._update_position(actor, angle)
			angle -= step

	def _update_position(self, actor, angle):
		x = math.cos(angle) * self._radium + self._radium
		y = math.sin(angle) * self._radium + self._radium
		actor.set_position(int(x), int(y))
