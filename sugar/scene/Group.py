from sugar.scene.Actor import Actor
from sugar.scene.Transformation import Transformation

class Group(Actor):
	def __init__(self):
		self._actors = []
		self._layout = None
		self._transf = Transformation()

	def set_position(self, x, y):
		Actor.set_position(self, x, y)
		self._transf.set_translation(x, y)

	def add(self, actor):
		self._actors.append(actor)
		self.do_layout()

	def remove(self, actor):
		self._actors.remove(actor)
		self.do_layout()

	def get_actors(self):
		return self._actors

	def set_layout(self, layout):
		self._layout = layout
		self.do_layout()

	def get_layout(self):
		return self._layout

	def do_layout(self):
		if self._layout:
			self._layout.layout_group(self)

	def render(self, drawable, transf):
		transf = transf.compose(self._transf)
		for actor in self._actors:
			actor.render(drawable, transf)
