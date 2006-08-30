from sugar.canvas.IconColor import IconColor

class Friend:
	def __init__(self, name, color):
		self._name = name
		self._color = color

	def get_name(self):
		return name

	def get_color(self):
		return IconColor(self._color)

class Friends(list):
	def __init__(self):
		list.__init__(self)

	def add_buddy(self, buddy):
		self.add(Friend(buddy.get_name(), buddy.get_color()))
