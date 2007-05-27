# Copyright (C) 2006, Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""D-bus service providing access to the shell's functionality"""
import dbus

from sugar.activity import ActivityRegistry
from sugar.activity import ActivityInfo

from model import bundleregistry

_DBUS_SERVICE = "org.laptop.Shell"
_DBUS_ACTIVITY_REGISTRY_IFACE = "org.laptop.Shell.ActivityRegistry"
_DBUS_OWNER_IFACE = "org.laptop.Shell.Owner"
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
        self._home_model.connect('active-activity-changed',
                                 self._cur_activity_changed_cb)

        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_DBUS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _DBUS_PATH)

    @dbus.service.method(_DBUS_ACTIVITY_REGISTRY_IFACE,
                         in_signature="s", out_signature="b")
    def AddBundle(self, bundle_path):
        """Register the activity bundle with the global registry 
        
        bundle_path -- path to the activity bundle's root directory,
            that is, the directory with activity/activity.info as a 
            child of the directory.
        
        The bundleregistry.BundleRegistry is responsible for setting 
        up a set of d-bus service mappings for each available activity.
        """
        registry = bundleregistry.get_registry()
        return registry.add_bundle(bundle_path)

    @dbus.service.method(_DBUS_ACTIVITY_REGISTRY_IFACE,
                         in_signature="s", out_signature="aa{sv}")
    def GetActivitiesForName(self, name):
        result = []
        key = name.lower()

        for bundle in bundleregistry.get_registry():
            name = bundle.get_name().lower()
            service_name = bundle.get_service_name().lower()
            if name.find(key) != -1 or service_name.find(key) != -1:
                result.append(self._get_activity_info(bundle).to_dict())

        return result

    @dbus.service.method(_DBUS_ACTIVITY_REGISTRY_IFACE,
                         in_signature="s", out_signature="aa{sv}")
    def GetActivitiesForType(self, mime_type):
        result = []

        for bundle in bundleregistry.get_registry():
            service_name = bundle.get_service_name().lower()
            if mime_type in bundle.get_mime_types():
                result.append(self._get_activity_info(bundle).to_dict())

        return result

    @dbus.service.signal(_DBUS_OWNER_IFACE, signature="s")
    def ColorChanged(self, color):
        pass

    def _owner_color_changed_cb(self, new_color):
        self.ColorChanged(new_color.to_string())

    @dbus.service.signal(_DBUS_OWNER_IFACE, signature="s")
    def NickChanged(self, nick):
        pass

    def _owner_nick_changed_cb(self, new_nick):
        self.NickChanged(new_nick)

    @dbus.service.signal(_DBUS_OWNER_IFACE, signature="ay")
    def IconChanged(self, icon_data):
        pass

    def _owner_icon_changed_cb(self, new_icon):
        self.IconChanged(dbus.ByteArray(new_icon))

    @dbus.service.signal(_DBUS_OWNER_IFACE, signature="s")
    def CurrentActivityChanged(self, activity_id):
        pass

    def _cur_activity_changed_cb(self, owner, new_activity):
        new_id = ""
        if new_activity:
            new_id = new_activity.get_activity_id()
        self.CurrentActivityChanged(new_id)

    def _get_activity_info(self, bundle):
        return ActivityInfo(bundle.get_name(), bundle.get_icon(),
                            bundle.get_service_name(), bundle.get_path())
