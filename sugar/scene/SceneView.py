import gtk

class SceneView(gtk.Fixed):
	def __init__(self, stage):
		gtk.Fixed.__init__(self)
		self.set_has_window(True)
		self.connect('expose-event', self.__expose_cb)

		self._stage = stage
		stage.connect('changed', self.__stage_changed_cb)

	def __expose_cb(self, widget, event):
		self._stage.render(widget.window)

	def __stage_changed_cb(self, stage):
		self.window.invalidate_rect(None, False)
