import random
import math

class IconLayout:
	DISTANCE_THRESHOLD = 120.0

	def __init__(self, grid):
		self._icons = []
		self._grid = grid

		[self._x1, self._y1] = self._grid.convert_to_canvas(1, 1)
		[self._x2, self._y2] = self._grid.convert_to_canvas(78, 59)

	def add_icon(self, icon):
		self._icons.append(icon)
		self._layout_icon(icon)

	def remove_icon(self, icon):
		self._icons.remove(icon)

	def _distance(self, icon1, icon2):
		a = icon2.props.x - icon1.props.x
		b = icon2.props.y - icon1.props.y
		return math.sqrt(a * a  + b * b)

	def _spread_icons(self):
		self._stable = True

		for icon1 in self._icons:
			vx = 0
			vy = 0

			for icon2 in self._icons:
				if icon1 != icon2:
					distance = self._distance(icon1, icon2)
					if distance <= IconLayout.DISTANCE_THRESHOLD:
						self._stable = False
						vx += icon1.props.x - icon2.props.x
						vy += icon1.props.y - icon2.props.y

			new_x = icon1.props.x + vx
			new_y = icon1.props.y + vy

			new_x = max(self._x1, new_x)
			new_y = max(self._y1, new_y)

			new_x = min(self._x2 - icon1.props.size, new_x)
			new_y = min(self._y2 - icon1.props.size, new_y)

			icon1.props.x = new_x
			icon1.props.y = new_y

	def _layout_icon(self, icon):
		x = random.random() * (self._x2 - self._x1 - icon.props.size) 
		y = random.random() * (self._y2 - self._y1 - icon.props.size)

		icon.props.x = x + self._x1
		icon.props.y = y + self._y1

		tries = 10
		self._spread_icons()
		while not self._stable and tries > 0:
			self._spread_icons()
			tries -= 1
