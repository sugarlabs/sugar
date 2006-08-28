import math

import goocanvas

from sugar.canvas.IconItem import IconItem

class PieceIcon(IconItem):
	def __init__(self, piece_item, **kwargs):
		IconItem.__init__(self, size=48, **kwargs)
		self._piece_item = piece_item

	def construct(self):
		angle_start = self._piece_item.get_angle_start()
		angle_end = self._piece_item.get_angle_end()
		radius = self.get_parent().get_radius()
		inner_radius = self.get_parent().get_inner_radius()

		icon_radius = (radius + inner_radius) / 2
		icon_angle = (angle_start + angle_end) / 2
		x = icon_radius * math.cos(icon_angle)
		y = - icon_radius * math.sin(icon_angle)

		icon_width = self.get_property('width')
		icon_height = self.get_property('height')
		self.set_property('x', x - icon_width / 2)
		self.set_property('y', y - icon_height / 2)

class PieceItem(goocanvas.Path):
	def __init__(self, angle_start, angle_end, **kwargs):
		goocanvas.Path.__init__(self, **kwargs)
		self._angle_start = angle_start
		self._angle_end = angle_end

		self.set_property('fill-color', '#e8e8e8')
		self.set_property('stroke-color', '#d8d8d8')
		self.set_property('line-width', 4)

	def get_icon(self):
		return self._icon

	def set_icon(self, icon_name, color):
		self._icon = PieceIcon(self, icon_name=icon_name, color=color)
		self.get_parent().add_child(self._icon)
		self._icon.construct()

	def get_angle_start(self):
		return self._angle_start

	def get_angle_end(self):
		return self._angle_end

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

		bg = goocanvas.Ellipse(radius_x=radius, radius_y=radius,
							   fill_color='#c2c3c5', line_width=0)
		self.add_child(bg)

		self._inner_radius = radius / 2
		fg = goocanvas.Ellipse(radius_x=self._inner_radius,
							   radius_y=self._inner_radius,
							   fill_color='#d8d8d8', line_width=0)
		self.add_child(fg)

	def add_piece(self, perc, icon_name, color):
		# FIXME can't override set_parent on the
		# PieceItem and there is no signal. So we
		# call a construct method on the childs for now.

		angle_end = self._angle_start + perc * 2 * math.pi / 100
		piece_item = PieceItem(self._angle_start, angle_end)
		self._angle_start = angle_end

		self.add_child(piece_item, 1)
		piece_item.construct()
		piece_item.set_icon(icon_name, color)

		return piece_item

	def remove_piece(self, piece_item):
		index = self.find_child(piece_item)
		self.remove_child(index)

		icon = piece_item.get_icon()
		index = self.find_child(icon)
		self.remove_child(index)

	def get_radius(self):
		return self._radius

	def get_inner_radius(self):
		return self._inner_radius
