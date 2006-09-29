import gtk
import cairo


class OverlayWindow(gtk.Window):
	def __init__(self, lower_window):
		gtk.Window.__init__(self)

		colormap = self.get_screen().get_rgba_colormap()
		colormap=None
		if not colormap:
			raise RuntimeError("The window manager doesn't support compositing.")
		self.set_colormap(colormap)

		self.realize()

		self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.window.set_accept_focus(False)
		self.window.set_transient_for(lower_window)

		self.set_decorated(False)
		self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
		self.set_default_size(gtk.gdk.screen_width(), gtk.gdk.screen_height())
		self.set_app_paintable(True)

		self.connect('expose-event', self._expose_cb)

	def _expose_cb(self, widget, event):
		cr = widget.window.cairo_create()
		cr.set_source_rgba(0.0, 0.0, 0.0, 0.4) # Transparent
		cr.set_operator(cairo.OPERATOR_SOURCE)
		cr.paint()
		return False

