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
 
import telepathyclient
from buddy import Buddy, Owner
from activity import Activity
import buddyiconcache
from sugar import profile


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

        self._icon_cache = buddyiconcache.BuddyIconCache()

        bus = dbus.SessionBus()
        self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE, bus=bus)        

        # Create the Owner object
        objid = self._get_next_object_id()
        self._owner = Owner(self, self._bus_name, objid, self._icon_cache)
        self._buddies[self._owner.get_key()] = self._owner

        self._registry = ManagerRegistry()
        self._registry.LoadManagers()

        self._server_client = self._connect_to_server()
        self._handles[self._server_client] = {}

        # Telepathy link local connection
        self._ll_client = None

        self._server_client.connect('contact-online', self._contact_online)
        self._server_client.connect('contact-offline', self._contact_offline)
        self._server_client.run()

        dbus.service.Object.__init__(self, self._bus_name, _PRESENCE_PATH)

    def _connect_to_server(self):
        protocol = 'jabber'
        account = {
            'account': 'olpc@collabora.co.uk',
            'password': 'learn',
            'server': 'light.bluelinux.co.uk'
        }

        mgr = self._registry.GetManager('gabble')
        conn = None

        # Search existing connections, if any, that we might be able to use
        connections = Connection.get_connections()
        for item in connections:
            if item[CONN_INTERFACE].GetProtocol() != protocol:
                continue
            if not item.object_path.startswith("/org/freedesktop/Telepathy/Connection/gabble/jabber/"):
                continue
            if item[CONN_INTERFACE].GetStatus() == CONNECTION_STATUS_CONNECTED:
                self_name = account['account']
                test_handle = item[CONN_INTERFACE].RequestHandles(CONNECTION_HANDLE_TYPE_CONTACT, [self_name])[0]
                if item[CONN_INTERFACE].GetSelfHandle() != test_handle:
                    continue
            conn = item

        if not conn:
            conn_bus_name, conn_object_path = \
                    mgr[CONN_MGR_INTERFACE].RequestConnection(protocol, account)
            conn = Connection(conn_bus_name, conn_object_path)

        return telepathyclient.TelepathyClient(conn)

    def _contact_online(self, tp, handle, key):
        buddy = self._buddies.get(key)

        if not buddy:
            # we don't know yet this buddy
            objid = self._get_next_object_id()
            buddy = Buddy(self._bus_name, objid, self._icon_cache)
            buddy.set_key(key)
            print "create buddy"
            self._buddies[key] = buddy

        buddies = self._handles[tp]
        buddies[handle] = buddy

        self.BuddyAppeared(buddy.object_path())
        
    def _contact_offline(self, tp, handle):
        buddy = self._handles[tp].pop(handle)
        key = buddy.get_key()

        # TODO: check if we don't see this buddy using the other CM
        self._buddies.pop(key)
        print "remove buddy"

        self.BuddyDisappeared(buddy.object_path())

    def _get_next_object_id(self):
        """Increment and return the object ID counter."""
        self._next_object_id = self._next_object_id + 1
        return self._next_object_id

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
