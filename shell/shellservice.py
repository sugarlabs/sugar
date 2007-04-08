import dbus

from sugar.activity import bundleregistry

_DBUS_SERVICE = "org.laptop.Shell"
_DBUS_INTERFACE = "org.laptop.Shell"
_DBUS_OWNER_INTERFACE = "org.laptop.Shell.Owner"
_DBUS_PATH = "/org/laptop/Shell"

class ShellService(dbus.service.Object):

    def __init__(self, shell_model):
        self._shell_model = shell_model

        self._owner = self._shell_model.get_owner()
        self._owner.connect('nick-changed', self._owner_nick_changed_cb)
        self._owner.connect('icon-changed', self._owner_icon_changed_cb)
        self._owner.connect('color-changed', self._owner_color_changed_cb)

        self._home_model = self._shell_model.get_home()
        self._home_model.connect('active-activity-changed', self._cur_activity_changed_cb)

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_DBUS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _DBUS_PATH)

    @dbus.service.method(_DBUS_INTERFACE, in_signature="s", out_signature="b")
    def add_bundle(self, bundle_path):
        registry = bundleregistry.get_registry()
        return registry.add_bundle(bundle_path)

    @dbus.service.signal(_DBUS_OWNER_INTERFACE, signature="s")
    def ColorChanged(self, color):
        pass

    def _owner_color_changed_cb(self, new_color):
        self.ColorChanged(new_color.to_string())

    @dbus.service.signal(_DBUS_OWNER_INTERFACE, signature="s")
    def NickChanged(self, nick):
        pass

    def _owner_nick_changed_cb(self, new_nick):
        self.NickChanged(new_nick)

    @dbus.service.signal(_DBUS_OWNER_INTERFACE, signature="ay")
    def IconChanged(self, icon_data):
        pass

    def _owner_icon_changed_cb(self, new_icon):
        self.IconChanged(dbus.ByteArray(new_icon))

    @dbus.service.signal(_DBUS_OWNER_INTERFACE, signature="s")
    def CurrentActivityChanged(self, activity_id):
        pass

    def _cur_activity_changed_cb(self, owner, new_activity):
        new_id = ""
        if new_activity:
            new_id = new_activity.get_activity_id()
        self.CurrentActivityChanged(new_id)
