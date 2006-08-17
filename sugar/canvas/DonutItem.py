import math

import goocanvas

class PieceItem(goocanvas.Path):
	def __init__(self, angle_start, angle_end, **kwargs):
		goocanvas.Path.__init__(self, **kwargs)
		self._angle_start = angle_start
		self._angle_end = angle_end

	def construct(self):
		r = self.get_parent().get_radius()

		data = 'M0,0 '

		dx = r * math.cos(self._angle_start)
		dy = - r * math.sin(self._angle_start)

		data += 'l%f,%f ' % (dx, dy)

		dx = r * math.cos(self._angle_end)
		dy = - r * math.sin(self._angle_end)

		data += 'A%f,%f 0 0,0 %f,%f ' % (r, r, dx, dy)

		data += 'z'

		self.set_property('data', data)

class DonutItem(goocanvas.Group):
	def __init__(self, radius, **kwargs):
		goocanvas.Group.__init__(self, **kwargs)
		self._radius = radius
		self._angle_start = 0

	def add_piece(self, perc):
		angle_end = self._angle_start + perc * 2 * math.pi / 100
		piece_item = PieceItem(self._angle_start, angle_end)
		self._angle_start = angle_end

		# FIXME can't override set_parent on the
		# PieceItem and there is no signal.
		self.add_child(piece_item)
		piece_item.construct()

		return piece_item

	def remove_piece(self, piece_item):
		index = self.find(piece_item)
		self.remove_child(index)

	def get_radius(self):
		return self._radius
