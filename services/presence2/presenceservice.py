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


_PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
_PRESENCE_INTERFACE = "org.laptop.Sugar.Presence"
_PRESENCE_PATH = "/org/laptop/Sugar/Presence"


class NotFoundError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'


class PresenceService(dbus.service.Object):
    def __init__(self):
        bus = dbus.SessionBus()
        self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE, bus=bus)        
        dbus.service.Object.__init__(self, self._bus_name, _PRESENCE_PATH)

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
        return []

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="s", out_signature="o")
    def GetActivityById(self, actid):
        return NotFoundError("The activity was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetBuddies(self):
        return []

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="ay", out_signature="o")
    def GetBuddyByPublicKey(self, key):
        return NotFoundError("The buddy was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="o")
    def GetOwner(self):
        return NotFoundError("The owner was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="sssa{sv}", out_signature="o")
    def ShareActivity(self, actid, atype, name, properties):
        return NotImplemented("not implemented yet")


def main():
    loop = gobject.MainLoop()
    ps = PresenceService()
    try:
        loop.run()
    except KeyboardInterrupt:
        print 'Ctrl+C pressed, exiting...'

if __name__ == "__main__":
    main()
