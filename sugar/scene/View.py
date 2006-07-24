import gtk

from sugar.scene.Stage import Stage

class View(gtk.DrawingArea):
	def __init__(self, stage):
		gtk.DrawingArea.__init__(self)

		self._stage = stage
		self._stage.connect('changed', self.__stage_changed_cb)
		self.connect('expose_event', self.__expose_cb)

	def __stage_changed_cb(self, stage):
		if self.window:
			self.window.invalidate_rect(None, False)

	def __expose_cb(self, widget, event):
		self._stage.render(widget.window)

	def get_stage(self):
		return self._stage
