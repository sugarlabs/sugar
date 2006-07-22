import math

from sugar.scene.LayoutManager import LayoutManager

class CircleLayout(LayoutManager):
	def __init__(self, radius):
		LayoutManager.__init__(self)

		self._radius = radius
		self._angle = 0

	def set_angle(self, angle):
		self._angle = angle

	def layout_group(self, group):
		step = 2 * math.pi / len(group.get_actors())
		angle = self._angle
		for actor in group.get_actors():
			self._update_position(actor, angle)
			angle += step

	def _update_position(self, actor, angle):
		x = math.cos(angle) * self._radius + self._radius
		y = math.sin(angle) * self._radius + self._radius
		actor.set_position(int(x + 0.5), int(y + 0.5))
