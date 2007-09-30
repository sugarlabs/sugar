import os

import gtk
import hippo

from sugar.graphics.roundbox import CanvasRoundBox

class Console(gtk.Window):
    def __init__(self, shell_model):
        gtk.Window.__init__(self)

        self._shell_model = shell_model

        self.set_default_size(gtk.gdk.screen_width() * 3 / 4,
                              gtk.gdk.screen_height() * 3 / 4)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.connect('realize', self._realize_cb)

        canvas = hippo.Canvas()
        self.add(canvas)
        canvas.show()

        box = hippo.CanvasBox(padding=20, background_color=0x000000FF)
        canvas.set_root(box)

        self.registry = Registry()
        for module in self.registry.view_modules:
            box.append(module.create_view('shell'), hippo.PACK_EXPAND)

    def _realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

class Registry(object):
    def __init__(self):
        self.view_modules = []

        base_extensions = [ 'console.logviewer' ]
        for extension in base_extensions:
            self.load_extension(extension)

    def load_extension(self, name):
        module = __import__(name)
        components = name.split('.')
        for component in components[1:]:
            module = getattr(module, component)

        self.view_modules.append(module)
