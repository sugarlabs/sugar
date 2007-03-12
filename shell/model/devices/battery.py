import gobject

from model.devices import device

class Device(device.Device):
    __gproperties__ = {
        'level' : (int, None, None, 0, 100, 0,
                   gobject.PARAM_READABLE)
    }

    def __init__(self):
        device.Device.__init__(self)
        self._level = 0

    def do_get_property(self, pspec):
        if pspec.name == 'level':
            return self._level 

    def get_type(self):
        return 'battery'
