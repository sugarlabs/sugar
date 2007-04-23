#!/usr/bin/env python
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

class NotFoundError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'


_ACTIVITY_PATH = "/org/laptop/Sugar/Presence/Activities/"
_ACTIVITY_INTERFACE = "org.laptop.Sugar.Presence.Activity"

class TestActivity(dbus.service.Object):
    def __init__(self, bus_name, object_id, actid, name, color, atype):
        self._actid = actid
        self._name = name
        self._color = color
        self._type = atype
        self._buddies = {}

        self._object_id = object_id
        self._object_path = _ACTIVITY_PATH + str(self._object_id)
        dbus.service.Object.__init__(self, bus_name, self._object_path)

    @dbus.service.signal(_ACTIVITY_INTERFACE, signature="o")
    def BuddyJoined(self, buddy_path):
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE, signature="o")
    def BuddyLeft(self, buddy_path):
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE, signature="o")
    def NewChannel(self, channel_path):
        pass

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="s")
    def GetId(self):
        return self._actid

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="s")
    def GetColor(self):
        return self._color

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="s")
    def GetType(self):
        return self._type

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="",
                        async_callbacks=('async_cb', 'async_err_cb'))
    def Join(self, async_cb, async_err_cb):
        pass

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="ao")
    def GetJoinedBuddies(self):
        return []

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="soao")
    def GetChannels(self):
        return None

    @dbus.service.method(_ACTIVITY_INTERFACE, in_signature="", out_signature="s")
    def GetName(self):
        return self._name


_BUDDY_PATH = "/org/laptop/Sugar/Presence/Buddies/"
_BUDDY_INTERFACE = "org.laptop.Sugar.Presence.Buddy"
_OWNER_INTERFACE = "org.laptop.Sugar.Presence.Buddy.Owner"

_PROP_NICK = "nick"
_PROP_KEY = "key"
_PROP_ICON = "icon"
_PROP_CURACT = "current-activity"
_PROP_COLOR = "color"
_PROP_OWNER = "owner"

class TestBuddy(dbus.service.Object):
    def __init__(self, bus_name, object_id, pubkey, nick, color):
        self._key = pubkey
        self._nick = nick
        self._color = color
        self._owner = False
        self._curact = None
        self._icon = ""
        self._activities = {}

        self._object_id = object_id
        self._object_path = _BUDDY_PATH + str(self._object_id)
        dbus.service.Object.__init__(self, bus_name, self._object_path)

    @dbus.service.signal(_BUDDY_INTERFACE, signature="ay")
    def IconChanged(self, icon_data):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE, signature="o")
    def JoinedActivity(self, activity_path):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE, signature="o")
    def LeftActivity(self, activity_path):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE, signature="a{sv}")
    def PropertyChanged(self, updated):
        pass

    # dbus methods
    @dbus.service.method(_BUDDY_INTERFACE, in_signature="", out_signature="ay")
    def GetIcon(self):
        return dbus.ByteArray(self._icon)

    @dbus.service.method(_BUDDY_INTERFACE, in_signature="", out_signature="ao")
    def GetJoinedActivities(self):
        acts = []
        for key in self._activities.keys():
            acts.append(dbus.ObjectPath(key))
        return acts

    @dbus.service.method(_BUDDY_INTERFACE, in_signature="", out_signature="a{sv}")
    def GetProperties(self):
        props = {}
        props[_PROP_NICK] = self._nick
        props[_PROP_OWNER] = self._owner
        props[_PROP_KEY] = self._key
        props[_PROP_COLOR] = self._color
        if self._curact:
            props[_PROP_CURACT] = self._curact
        else:
            props[_PROP_CURACT] = ""
        return props

_OWNER_PUBKEY = "AAAAB3NzaC1kc3MAAACBAKEVDFJW9D9GK20QFYRKbhV7kpjnhKkkzudn34ij" \
                "Ixje+x1ZXTIU6J1GFmJYrHq9uBRi72lOVAosGUop+HHZFRyTeYLxItmKfIoD" \
                "S2rwyL9cGRoDsD4yjECMqa2I+pGxriw4OmHeu5vmBkk+5bXBdkLf0EfseuPC" \
                "lT7FE+Fj4C6FAAAAFQCygOIpXXybKlVTcEfprOQp3Uud0QAAAIBjyjQhOWHq" \
                "FdJlALmnriQR+Zi1i4N/UMjWihF245RXJuUU6DyYbx4QxznxRnYKx/ZvsD0O" \
                "9+ihzmQd6eFwU/jQ6sxiL7DSlCJ3axgG9Yvbf7ELeXGo4/Z9keOVdei0sXz4" \
                "VBvJC0c0laELsnU0spFC62qQKxNemTbXDGksauj19gAAAIEAmcvY8VX47pRP" \
                "k7MjrDzZlPvvNQgHMNZSwHGIsF7EMGVDCYpbQTyR+cmtJBBFVyxtNbK7TWTZ" \
                "K8uH1tm9GyMcViUdIT4xCirA0JanE597KdlBz39l/623wF4jvbnnHOZ/pIT9" \
                "tPd1pCYJf+L7OEKCBUAyQhcq159X8A1toM48Soc="
_OWNER_PRIVKEY = "MIIBuwIBAAKBgQChFQxSVvQ/RittEBWESm4Ve5KY54SpJM7nZ9+IoyMY3vs" \
                 "dWV0yFOidRhZiWKx6vbgUYu9pTlQKLBlKKfhx2RUck3mC8SLZinyKA0tq8M" \
                 "i/XBkaA7A+MoxAjKmtiPqRsa4sODph3rub5gZJPuW1wXZC39BH7HrjwpU+x" \
                 "RPhY+AuhQIVALKA4ildfJsqVVNwR+ms5CndS53RAoGAY8o0ITlh6hXSZQC5" \
                 "p64kEfmYtYuDf1DI1ooRduOUVyblFOg8mG8eEMc58UZ2Csf2b7A9Dvfooc5" \
                 "kHenhcFP40OrMYi+w0pQid2sYBvWL23+xC3lxqOP2fZHjlXXotLF8+FQbyQ" \
                 "tHNJWhC7J1NLKRQutqkCsTXpk21wxpLGro9fYCgYEAmcvY8VX47pRPk7Mjr" \
                 "DzZlPvvNQgHMNZSwHGIsF7EMGVDCYpbQTyR+cmtJBBFVyxtNbK7TWTZK8uH" \
                 "1tm9GyMcViUdIT4xCirA0JanE597KdlBz39l/623wF4jvbnnHOZ/pIT9tPd" \
                 "1pCYJf+L7OEKCBUAyQhcq159X8A1toM48SocCFAvkZYCYtLhSDEPrlf0jLD" \
                 "jrMz+i"
_OWNER_NICK = "TestOwner"
_OWNER_COLOR = "#75C228,#308C30"

class TestOwner(TestBuddy):
    def __init__(self, bus_name, object_id):
        TestBuddy.__init__(self, bus_name, object_id, _OWNER_PUBKEY,
                _OWNER_NICK, _OWNER_COLOR)
        self._owner = True


_PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
_PRESENCE_INTERFACE = "org.laptop.Sugar.Presence"
_PRESENCE_PATH = "/org/laptop/Sugar/Presence"

class TestPresenceService(dbus.service.Object):
    """A test D-Bus PresenceService used to exercise the Sugar PS bindings."""

    def __init__(self):
        self._next_object_id = 0
        self._activities = {}
        self._buddies = {}

        self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE,
                                              bus=dbus.SessionBus())

        objid = self._get_next_object_id()
        self._owner = TestOwner(self._bus_name, objid)

        dbus.service.Object.__init__(self, self._bus_name, _PRESENCE_PATH)

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

    @dbus.service.signal(_PRESENCE_INTERFACE, signature="o")
    def ActivityInvitation(self, activity):
        pass

    @dbus.service.signal(_PRESENCE_INTERFACE, signature="soo")
    def PrivateInvitation(self, bus_name, connection, channel):
        pass

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetActivities(self):
        ret = []
        for act in self._activities.values():
            ret.append(dbus.ObjectPath(act._object_path))
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="s", out_signature="o")
    def GetActivityById(self, actid):
        if self._activities.has_key(actid):
            return dbus.ObjectPath(self._activities[actid]._object_path)
        raise NotFoundError("The activity was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetBuddies(self):
        ret = []
        for buddy in self._buddies.values():
            ret.append(buddy._object_path)
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="ay", out_signature="o")
    def GetBuddyByPublicKey(self, key):
        key = ''.join([chr(item) for item in key])
        if self._buddies.has_key(key):
            return self._buddies[key]._object_path
        raise NotFoundError("The buddy was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="o")
    def GetOwner(self):
        if not self._owner:
            raise NotFoundError("The owner was not found.")
        return dbus.ObjectPath(self._owner._object_path)

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="sssa{sv}",
            out_signature="o", async_callbacks=('async_cb', 'async_err_cb'))
    def ShareActivity(self, actid, atype, name, properties, async_cb, async_err_cb):
        pass

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="so")
    def GetPreferredConnection(self):
        return "bar.baz.foo", "/bar/baz/foo"

def main():
    loop = gobject.MainLoop()
    ps = TestPresenceService()
    loop.run()

if __name__ == "__main__":
    main()
