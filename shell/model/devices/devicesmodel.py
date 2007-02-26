import gobject

from model.devices import device
from model.devices import wirednetwork
from model.devices import wirelessnetwork
from model.devices import battery
from hardware import hardwaremanager
from hardware import nmclient

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

        self._devices = {}
        self.add_device(battery.Device())

        self._observe_network_manager()

    def _observe_network_manager(self):
        network_manager = hardwaremanager.get_network_manager()

        for device in network_manager.get_devices():
            self._check_network_device(device)

        network_manager.connect('device-activated',
                                self._network_device_activated_cb)
        network_manager.connect('device-removed',
                                self._network_device_removed_cb)

    def _network_device_activated_cb(self, network_manager, nm_device):
        self._check_network_device(nm_device)

    def _network_device_removed_cb(self, nm_device):
        self._remove_network_device(nm_device)

    def _network_device_state_changed_cb(self, nm_device):
        if nm_device.get_state == nmclient.DEVICE_STATE_INACTIVE:
            self._remove_network_device(nm_device)

    def _check_network_device(self, nm_device):
        if not nm_device.is_valid():
            return

        if nm_device.get_type() == nmclient.DEVICE_TYPE_802_11_WIRELESS:
            self._add_network_device(nm_device)

    def _get_network_device(self, nm_device):
        return self._devices[nm_device.get_op()]

    def _add_network_device(self, nm_device):
        self.add_device(wirelessnetwork.Device(nm_device))
        nm_device.connect('state-changed',
                          self._network_device_state_changed_cb)

    def _remove_network_device(self, nm_device):
        self.remove_device(self._get_network_device(nm_device))

    def __iter__(self):
        return iter(self._devices.values())

    def add_device(self, device):
        self._devices[device.get_id()] = device
        self.emit('device-appeared', device)

    def remove_device(self, device):
        self.emit('device-disappeared', self._devices[device.get_id()])
        del self._devices[device.get_id()]
