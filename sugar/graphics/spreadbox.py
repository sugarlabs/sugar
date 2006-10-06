import random
import math

import cairo
import hippo

_DISTANCE_THRESHOLD = 120.0

class SpreadBox(hippo.CanvasBox, hippo.CanvasItem):
	__gtype_name__ = 'SugarSpreadBox'

	def __init__(self, **kwargs):
		hippo.CanvasBox.__init__(self, **kwargs)

		self._items_to_position = []
		self._spread_on_add = False
		self._stable = False

	def add(self, item):
		self._items_to_position.append(item)
		self.append(item, hippo.PACK_FIXED)
		if self._spread_on_add:
			self.spread()

	def spread(self):
		self._spread_on_add = True

		[width, height] = self.get_allocation()
		for item in self._items_to_position:
			x = int(random.random() * width)
			y = int(random.random() * height)

			[x, y] = self._clamp_position(item, x, y)
			self.move(item, x, y)

		self._items_to_position = []

	def _get_distance(self, icon1, icon2):
		[icon1_x, icon1_y] = self.get_position(icon1)
		[icon2_x, icon2_y] = self.get_position(icon2)

		a = icon1_x - icon2_x
		b = icon1_y - icon2_y

		return math.sqrt(a * a  + b * b)

	def _get_repulsion(self, icon1, icon2):
		[icon1_x, icon1_y] = self.get_position(icon1)
		[icon2_x, icon2_y] = self.get_position(icon2)

		f_x = icon1_x - icon2_x
		f_y = icon1_y - icon2_y

		return [f_x, f_y]

	def _clamp_position(self, icon, x, y):
		x = max(0, x)
		y = max(0, y)

		item_w = icon.get_width_request()
		item_h = icon.get_height_request(item_w)
		[box_w, box_h] = self.get_allocation()

		x = min(box_w - item_w, x)
		y = min(box_h - item_h, y)

		return [x, y]

	def _spread_icons(self):
		self._stable = True

		for icon1 in self.get_children():
			vx = 0
			vy = 0

			for icon2 in self.get_children():
				if icon1 != icon2:
					distance = self._get_distance(icon1, icon2)
					if distance <= _DISTANCE_THRESHOLD:
						self._stable = False
						[f_x, f_y] = self._get_repulsion(icon1, icon2)
						vx += f_x
						vy += f_y

			if vx != 0 or vy != 0:
				[x, y] = self.get_position(icon1)
				new_x = x + vx
				new_y = y + vy

				[new_x, new_y] = self._clamp_position(icon1, new_x, new_y)

				self.move(icon1, new_x, new_y)

	def do_allocate(self, width, height):
		hippo.CanvasBox.do_allocate(self, width, height)

		tries = 10
		self._spread_icons()
		while not self._stable and tries > 0:
			self._spread_icons()
			tries -= 1
