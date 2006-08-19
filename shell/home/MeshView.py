import goocanvas

class Model(goocanvas.CanvasModelSimple):
	def __init__(self, data_model):
		goocanvas.CanvasModelSimple.__init__(self)

		root = self.get_root_item()

		item = goocanvas.Rect(width=1200, height=900,
							  fill_color="#4f4f4f")
		root.add_child(item)

class MeshView(goocanvas.CanvasView):
	def __init__(self, shell, data_model):
		goocanvas.CanvasView.__init__(self)
		self._shell = shell

		self.connect("item_view_created", self.__item_view_created_cb)

		canvas_model = Model(data_model)
		self.set_model(canvas_model)

	def __item_view_created_cb(self, view, item_view, item):
		pass
