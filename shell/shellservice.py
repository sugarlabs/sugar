"""D-bus service providing access to the shell's functionality"""
import dbus

from sugar.activity import bundleregistry

_DBUS_SERVICE = "org.laptop.Shell"
_DBUS_INTERFACE = "org.laptop.Shell"
_DBUS_OWNER_INTERFACE = "org.laptop.Shell.Owner"
_DBUS_PATH = "/org/laptop/Shell"

class ShellService(dbus.service.Object):
    """Provides d-bus service to script the shell's operations
    
    Uses a shell_model object to observe events such as changes to:
    
        * nickname 
        * colour
        * icon
        * currently active activity
    
    and pass the event off to the methods in the dbus signature.
    
    Key method here at the moment is add_bundle, which is used to 
    do a run-time registration of a bundle using it's application path.
    
    XXX At the moment the d-bus service methods do not appear to do
    anything other than add_bundle
    """
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
        """Register the activity bundle with the global registry 
        
        bundle_path -- path to the activity bundle's root directory,
            that is, the directory with activity/activity.info as a 
            child of the directory.
        
        The bundleregistry.BundleRegistry is responsible for setting 
        up a set of d-bus service mappings for each available activity.
        """
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
