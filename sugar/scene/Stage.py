from sugar.scene.Group import Group

class Stage(Group):
	def __init__(self):
		Group.__init__(self)
		self._fps = 50

	def get_fps(self):
		return self._fps

	def render(self, drawable):
		Group.render(self, drawable)
