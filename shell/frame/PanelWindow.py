import gtk

from sugar.canvas.CanvasWindow import CanvasWindow

class PanelWindow(CanvasWindow):
	def __init__(self, model):
		CanvasWindow.__init__(self, model)

		self.set_decorated(False)

		self.realize()
		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.window.set_accept_focus(False)

		screen = gtk.gdk.screen_get_default()
		self.window.set_transient_for(screen.get_root_window())
