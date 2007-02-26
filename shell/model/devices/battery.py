from model.devices import device

class Device(device.Device):
    def __init__(self):
        device.Device.__init__(self)

    def get_type(self):
        return 'battery'

    def get_level(self):
        return 0
