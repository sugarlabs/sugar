import gtk
import hippo

class PanelWindow(gtk.Window):
	def __init__(self):
		gtk.Window.__init__(self)

		self.set_decorated(False)
		self.connect('realize', self._realize_cb)

		canvas = hippo.Canvas()

		self._bg = hippo.CanvasBox(background_color=0x414141ff)
		canvas.set_root(self._bg)

		self.add(canvas)
		canvas.show()

	def get_root(self):
		return self._bg

	def _realize_cb(self, widget):
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.window.set_accept_focus(False)
