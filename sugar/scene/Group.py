from sugar.scene.Actor import Actor

class Group(Actor):
	def __init__(self):
		self._actors = []
		self._layout_manager = None

	def add(self, actor):
		self._actors.append(actor)
		if self._layout_manager:
			self._layout_manager.layout_group(slef)

	def remove(self, actor):
		self._actors.remove(actor)
		if self._layout_manager:
			self._layout_manager.layout_group(self)

	def get_actors(self):
		return self._actors

	def set_layout_manager(self, layout_manager):
		self._layout_manager = layout_manager
		self._layout_manager.layout_group(self)

	def render(self, drawable):
		for actor in self._actors:
			actor.render(drawable)
