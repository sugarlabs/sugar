# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""D-bus service providing access to the shell's functionality"""

import dbus
from gi.repository import Gtk

from jarabe.model import shell
from jarabe.model import bundleregistry


_DBUS_SERVICE = 'org.laptop.Shell'
_DBUS_SHELL_IFACE = 'org.laptop.Shell'
_DBUS_PATH = '/org/laptop/Shell'


class UIService(dbus.service.Object):
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

    def __init__(self):
        bus = dbus.SessionBus()
        bus_name = dbus.service.BusName(_DBUS_SERVICE, bus=bus)
        dbus.service.Object.__init__(self, bus_name, _DBUS_PATH)

        self._shell_model = shell.get_model()

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature='s', out_signature='s')
    def GetBundlePath(self, bundle_id):
        bundle = bundleregistry.get_registry().get_bundle(bundle_id)
        if bundle:
            return bundle.get_path()
        else:
            return ''

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature='s', out_signature='b')
    def ActivateActivity(self, activity_id):
        """Switch to the window related to this activity_id and return a
        boolean indicating if there is a real (ie. not a launcher window)
        activity already open.
        """
        activity = self._shell_model.get_activity_by_id(activity_id)

        if activity is not None and activity.get_window() is not None:
            activity.get_window().activate(Gtk.get_current_event_time())
            return self._shell_model.get_launcher(activity_id) is None

        return False

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature='ss', out_signature='')
    def NotifyLaunch(self, bundle_id, activity_id):
        shell.get_model().notify_launch(activity_id, bundle_id)

    @dbus.service.method(_DBUS_SHELL_IFACE,
                         in_signature='s', out_signature='')
    def NotifyLaunchFailure(self, activity_id):
        shell.get_model().notify_launch_failed(activity_id)
