# Copyright (C) 2007, Red Hat, Inc.
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

import gobject
import dbus, dbus.service, dbus.glib
from telepathy.client import ManagerRegistry, Connection
from telepathy.interfaces import (CONN_MGR_INTERFACE, CONN_INTERFACE)
from telepathy.constants import (CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_DISCONNECTED, CONNECTION_HANDLE_TYPE_CONTACT)
 
from server_plugin import ServerPlugin
from linklocal_plugin import LinkLocalPlugin

from buddy import Buddy, Owner
from activity import Activity

_PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
_PRESENCE_INTERFACE = "org.laptop.Sugar.Presence"
_PRESENCE_PATH = "/org/laptop/Sugar/Presence"


class NotFoundError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'


class PresenceService(dbus.service.Object):
    def __init__(self):
        self._next_object_id = 0

        self._buddies = {}      # key -> Buddy
        self._handles = {}      # tp client -> (handle -> Buddy)
        self._activities = {}   # activity id -> Activity

        bus = dbus.SessionBus()
        self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE, bus=bus)        

        # Create the Owner object
        objid = self._get_next_object_id()
        self._owner = Owner(self, self._bus_name, objid)
        self._buddies[self._owner.get_key()] = self._owner

        self._registry = ManagerRegistry()
        self._registry.LoadManagers()

        # Set up the server connection
        self._server_plugin = ServerPlugin(self._registry)
        self._handles[self._server_plugin] = {}

        self._server_plugin.connect('status', self._server_status_cb)
        self._server_plugin.connect('contact-online', self._contact_online)
        self._server_plugin.connect('contact-offline', self._contact_offline)
        self._server_plugin.connect('avatar-updated', self._avatar_updated)
        self._server_plugin.connect('properties-changed', self._properties_changed)
        self._server_plugin.connect('activities-changed', self._activities_changed)
        self._server_plugin.start()

        # Set up the link local connection
        self._ll_plugin = LinkLocalPlugin(self._registry)
        self._handles[self._ll_plugin] = {}

        dbus.service.Object.__init__(self, self._bus_name, _PRESENCE_PATH)

    def _server_status_cb(self, plugin, status, reason):
        pass

    def _contact_online(self, tp, handle, key):
        new_buddy = False
        buddy = self._buddies.get(key)

        if not buddy:
            # we don't know yet this buddy
            objid = self._get_next_object_id()
            buddy = Buddy(self._bus_name, objid, handle=handle)
            buddy.set_key(key)
            print "create buddy", key
            self._buddies[key] = buddy
            new_buddy = True

        buddies = self._handles[tp]
        buddies[handle] = buddy

        # store the handle of the buddy for this CM
        buddy.handles[tp] = handle

        if new_buddy:
            self.BuddyAppeared(buddy.object_path())
        
    def _contact_offline(self, tp, handle):
        buddy = self._handles[tp].pop(handle)
        key = buddy.get_key()

        # the handle of the buddy for this CM is not valid anymore
        buddy.handles.pop(tp)

        if not buddy.handles:
            # we remove the last handle of the buddy, so we don't see
            # it anymore.
            self._buddies.pop(key)
            print "remove buddy"
            self.BuddyDisappeared(buddy.object_path())

    def _get_next_object_id(self):
        """Increment and return the object ID counter."""
        self._next_object_id = self._next_object_id + 1
        return self._next_object_id

    def _avatar_updated(self, tp, handle, avatar):
        buddy = self._handles[tp].get(handle)

        if buddy:
            buddy.set_icon(avatar)

    def _properties_changed(self, tp, handle, prop):
        buddy = self._handles[tp].get(handle)

        if buddy:
            buddy.set_properties(prop)

    def _activities_changed(self, tp, handle, prop):
        pass

    @dbus.service.signal(_PRESENCE_INTERFACE, signature="o")
    def ActivityAppeared(self, activity):
        pass

    @dbus.service.signal(_PRESENCE_INTERFACE, signature="o")
    def ActivityDisappeared(self, activity):
        pass

    @dbus.service.signal(_PRESENCE_INTERFACE, signature="o")
    def BuddyAppeared(self, buddy):
        pass

    @dbus.service.signal(_PRESENCE_INTERFACE, signature="o")
    def BuddyDisappeared(self, buddy):
        pass

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetActivities(self):
        ret = []
        for act in self._activities.values():
            ret.append(act.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="s", out_signature="o")
    def GetActivityById(self, actid):
        if self._activities.has_key(actid):
            return self._activities[actid].object_path()
        raise NotFoundError("The activity was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetBuddies(self):
        ret = []
        for buddy in self._buddies.values():
            ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="ay", out_signature="o")
    def GetBuddyByPublicKey(self, key):
        if self._buddies.has_key(key):
            return self._buddies[key].object_path()
        raise NotFoundError("The buddy was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="o")
    def GetOwner(self):
        if not self._owner:
            raise NotFoundError("The owner was not found.")
        else:
            return self._owner.get_object_path()

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="sssa{sv}", out_signature="o")
    def ShareActivity(self, actid, atype, name, properties):
        raise NotImplementedError("not implemented yet")


def main():
    loop = gobject.MainLoop()
    ps = PresenceService()
    try:
        loop.run()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'

if __name__ == "__main__":
    main()
