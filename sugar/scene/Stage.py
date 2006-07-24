from sugar.scene.Group import Group
from sugar.scene.Transformation import Transformation

class Stage(Group):
	def __init__(self):
		Group.__init__(self)
		self._fps = 50

	def get_fps(self):
		return self._fps

	def render(self, drawable, transf = None):
		if transf == None:
			transf = Transformation()
		Group.render(self, drawable, transf)
