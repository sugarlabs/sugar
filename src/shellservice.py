# Copyright (C) 2006-2007 Red Hat, Inc.
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
import os

from view import Shell
from model import shellmodel

_DBUS_SERVICE = "org.laptop.Shell"
_DBUS_SHELL_IFACE = "org.laptop.Shell"
_DBUS_OWNER_IFACE = "org.laptop.Shell.Owner"
_DBUS_PATH = "/org/laptop/Shell"

_DBUS_RAINBOW_IFACE = "org.laptop.security.Rainbow"

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

    _rainbow = None

    def __init__(self):
        self._shell = Shell.get_instance()
        self._shell_model = shellmodel.get_instance()

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

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature="s", out_signature="b")
    def ActivateActivity(self, activity_id):
        host = self._shell.get_activity(activity_id)
        if host:
            host.present()
            return True

        return False

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature="ss", out_signature="")
    def NotifyLaunch(self, bundle_id, activity_id):
        home = self._shell.get_model().get_home()
        home.notify_launch(activity_id, bundle_id)

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature="s", out_signature="")
    def NotifyLaunchFailure(self, activity_id):
        home = self._shell.get_model().get_home()
        home.notify_launch_failed(activity_id)

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

    def _get_rainbow_service(self):
        """Lazily initializes an interface to the Rainbow security daemon."""
        if self._rainbow is None:
            system_bus = dbus.SystemBus()
            obj = system_bus.get_object(_DBUS_RAINBOW_IFACE, '/',
                                        follow_name_owner_changes=True)
            self._rainbow = dbus.Interface(obj,
                                           dbus_interface=_DBUS_RAINBOW_IFACE)
        return self._rainbow

    @dbus.service.signal(_DBUS_OWNER_IFACE, signature="s")
    def CurrentActivityChanged(self, activity_id):
        if os.path.exists('/etc/olpc-security'):
            self._get_rainbow_service().ChangeActivity(
                    activity_id,
                    dbus_interface=_DBUS_RAINBOW_IFACE)

    def _cur_activity_changed_cb(self, owner, new_activity):
        new_id = ""
        if new_activity:
            new_id = new_activity.get_activity_id()
        if new_id:
            self.CurrentActivityChanged(new_id)

