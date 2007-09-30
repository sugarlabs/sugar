import os

import gtk
import hippo

from sugar.graphics.roundbox import CanvasRoundBox

from model.shellmodel import ShellModel

class Console(gtk.Window):
    def __init__(self, shell_model):
        gtk.Window.__init__(self)

        self._shell_model = shell_model
        self._home_model = shell_model.get_home()
        self._shell_model.connect('notify::zoom-level',
                                  self._zoom_level_changed_cb)
        self._home_model.connect('active-activity-changed',
                                 self._active_activity_changed_cb)

        self.set_default_size(gtk.gdk.screen_width() * 5 / 6,
                              gtk.gdk.screen_height() * 5 / 6)
        self.set_decorated(False)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        self.connect('realize', self._realize_cb)

        self.canvas = hippo.Canvas()
        self.add(self.canvas)
        self.canvas.show()

        self.registry = Registry()
        self.context = 'shell'
        self._update_view()

    def _update_view(self):
        box = hippo.CanvasBox(padding=20, background_color=0x000000FF)
        self.canvas.set_root(box)

        for module in self.registry.view_modules:
            box.append(module.create_view(self.context), hippo.PACK_EXPAND)

    def _active_activity_changed_cb(self, home_model, activity):
        if self._shell_model.get_zoom_level() == ShellModel.ZOOM_HOME:
            self.context = 'activity:' + activity.get_type()
            self._update_view()

    def _zoom_level_changed_cb(self, shell_model, pspec):
        if shell_model.props.zoom_level == ShellModel.ZOOM_HOME:
            self.context = 'shell'
            self._update_view()
        elif shell_model.props.zoom_level == ShellModel.ZOOM_ACTIVITY:
            activity = self._home_model.get_active_activity()
            self.context = 'activity:' + activity.get_type()
            self._update_view()
        else:
            self.context = 'mesh'
            self._update_view()

    def _realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)

class Registry(object):
    def __init__(self):
        self.view_modules = []

        view_modules = [ 'console.logviewer' ]
        for module in view_modules:
            self.load_view_modules(module)

    def load_view_modules(self, name):
        module = __import__(name)
        components = name.split('.')
        for component in components[1:]:
            module = getattr(module, component)

        self.view_modules.append(module)
