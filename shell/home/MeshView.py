import goocanvas

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, shell):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

class MeshView(goocanvas.CanvasView):
	def __init__(self, shell):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(shell)
		self.set_model(canvas_model)

	def __item_view_created_cb(self, view, item_view, item):
		pass
