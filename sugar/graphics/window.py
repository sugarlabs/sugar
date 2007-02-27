import hippo
import gtk

class Window(gtk.Window):
    def __init__(self, window_type=gtk.WINDOW_TOPLEVEL):
        gtk.Window.__init__(self, window_type)

        self._canvas = hippo.Canvas()
        self.add(self._canvas)
        self._canvas.show()

    def set_root(self, root):
        self._canvas.set_root(root)

