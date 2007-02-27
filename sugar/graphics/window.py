import hippo
import gtk

class Window(gtk.Window):
    def __init__(self, window_type=gtk.WINDOW_TOPLEVEL):
        gtk.Window.__init__(self, window_type)

        self._canvas = hippo.Canvas()
        self.add(self._canvas)
        self._canvas.show()

        self._canvas.connect_after('realize', self._window_realize_cb)

    def set_root(self, root):
        self._canvas.set_root(root)

    def _window_realize_cb(self, canvas):
        canvas.window.set_back_pixmap(None, False)
