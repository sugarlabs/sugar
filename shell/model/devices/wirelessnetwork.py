import gobject

from model.devices import device

class Device(device.Device):
    __gproperties__ = {
        'name'     : (str, None, None, None,
                      gobject.PARAM_READABLE),
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE)
    }

    def __init__(self, nm_device):
        device.Device.__init__(self)
        self._nm_device = nm_device

        self._nm_device.connect('strength-changed',
                                self._strength_changed_cb)

    def _strength_changed_cb(self, nm_device, strength):
        self.notify('strength')

    def _essid_changed_cb(self, nm_device):
        self.notify('name')

    def do_get_property(self, pspec):
        if pspec.name == 'strength':
            return self._nm_device.get_strength()
        elif pspec.name == 'name':
            # FIXME
            return None

    def get_type(self):
        return 'wirelessnetwork'

    def get_id(self):
        return self._nm_device.get_op()
