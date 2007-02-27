import hippo
import gtk

from sugar.graphics import color

class _Style(gtk.Style):
    __gtype_name__ = 'SugarCanvasStyle'
    def __init__(self):
        gtk.Style.__init__(self)

    def do_set_background(self, window, state):
        window.set_back_pixmap(None, False)

class Window(gtk.Window):
    def __init__(self, window_type=gtk.WINDOW_TOPLEVEL):
        gtk.Window.__init__(self, window_type)

        self._canvas = hippo.Canvas()
        self._canvas.set_style(_Style())
        self.add(self._canvas)
        self._canvas.show()

    def set_root(self, root):
        self._canvas.set_root(root)
