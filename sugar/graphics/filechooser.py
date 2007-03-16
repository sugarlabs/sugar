import gtk

from sugar.graphics import units

class FileChooserDialog(gtk.FileChooserDialog):
    def __init__(self, title=None, parent=None,
                 action=gtk.FILE_CHOOSER_ACTION_OPEN, buttons=None):
        gtk.FileChooserDialog.__init__(self, title, parent, action, buttons)
        self.set_default_size(units.points_to_pixels(7 * 40),
                              units.points_to_pixels(7 * 30))
