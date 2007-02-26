import dbus

from sugar.activity import bundleregistry

_DBUS_SERVICE = "org.laptop.Shell"
_DBUS_INTERFACE = "org.laptop.Shell"
_DBUS_PATH = "/org/laptop/Shell"

class ShellService(dbus.service.Object):

    def __init__(self, shellModel):
        self._shellModel = shellModel

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_DBUS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _DBUS_PATH)
        
    @dbus.service.method(_DBUS_INTERFACE, in_signature="s", out_signature="b")
    def add_bundle(self, bundle_path):
        registry = bundleregistry.get_registry()
        return registry.add_bundle(bundle_path)
