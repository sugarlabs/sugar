class Actor:
	def __init__(self):
		self._x = 0
		self._y = 0
		self._width = -1
		self._height = -1

	def set_position(self, x, y):
		self._x = x
		self._y = y

	def set_size(self, width, height):
		self._width = width
		self._height = height

	def render(self, window, transf):
		pass
