import gobject

from model.devices import device
from model.devices import network
from model.devices import battery

class DevicesModel(gobject.GObject):
    __gsignals__ = {
        'device-appeared'   : (gobject.SIGNAL_RUN_FIRST,
                               gobject.TYPE_NONE, 
                              ([gobject.TYPE_PYOBJECT])),
        'device-disappeared': (gobject.SIGNAL_RUN_FIRST,
                               gobject.TYPE_NONE, 
                              ([gobject.TYPE_PYOBJECT]))
    }
   
    def __init__(self):
        gobject.GObject.__init__(self)

        self._devices = []

        self.add_device(network.Device())
        self.add_device(battery.Device())

    def __iter__(self):
        return iter(self._devices)

    def add_device(self, device):
        self._devices.append(device)
