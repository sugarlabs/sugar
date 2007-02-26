import gobject

from sugar import util

class Device(gobject.GObject):
    def __init__(self):
        gobject.GObject.__init__(self)
        self._id = util.unique_id()

    def get_type(self):
        return 'unknown'        

    def get_id(self):
        return self._id
