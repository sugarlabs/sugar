import random
import math

import cairo

_DISTANCE_THRESHOLD = 120.0

class SpreadLayout:
	def __init__(self):
		pass

	def _get_distance(self, box, icon1, icon2):
		[icon1_x, icon1_y] = box.get_position(icon1)
		[icon2_x, icon2_y] = box.get_position(icon2)

		a = icon1_x - icon2_x
		b = icon1_y - icon2_y

		return math.sqrt(a * a  + b * b)

	def _get_repulsion(self, box, icon1, icon2):
		[icon1_x, icon1_y] = box.get_position(icon1)
		[icon2_x, icon2_y] = box.get_position(icon2)

		f_x = icon1_x - icon2_x
		f_y = icon1_y - icon2_y

		return [f_x, f_y]

	def _clamp_position(self, box, icon, x, y):
		x = max(0, x)
		y = max(0, y)

		[item_w, item_h] = icon.get_allocation()
		[box_w, box_h] = box.get_allocation()

		x = min(box_w - item_w, x)
		y = min(box_h - item_h, y)

		return [x, y]

	def _spread_icons(self, box):
		stable = True

		for icon1 in box.get_children():
			vx = 0
			vy = 0

			[x, y] = box.get_position(icon1)

			for icon2 in box.get_children():
				if icon1 != icon2:
					distance = self._get_distance(box, icon1, icon2)
					if distance <= _DISTANCE_THRESHOLD:
						stable = False
						[f_x, f_y] = self._get_repulsion(box, icon1, icon2)
						vx += f_x
						vy += f_y

			new_x = x + vx
			new_y = y + vy

			[new_x, new_y] = self._clamp_position(box, icon1, new_x, new_y)

			box.move(icon1, new_x, new_y)

			return stable

	def layout(self, box):
		[width, height] = box.get_allocation()

		for item in box.get_children():
			[item_w, item_h] = item.get_allocation()

			x = int(random.random() * width)
			y = int(random.random() * height)

			[x, y] = self._clamp_position(box, item, x, y)

			box.move(item, x, y)

		tries = 10
		stable = self._spread_icons(box)
		while not stable and tries > 0:
			stable = self._spread_icons(box)
			tries -= 1
