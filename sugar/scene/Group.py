from sugar.scene.Actor import Actor

class Group(Actor):
	def __init__(self):
		self._actors = []

	def add(self, actor):
		self._actors.append(actor)

	def remove(self, actor):
		self._actors.remove(actor)

	def render(self, drawable):
		for actor in self._actors:
			actor.render(drawable)
