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
    def __init__(self, bus_name, object_id, parent, actid, name, color, atype, properties):
        self._parent = parent
        self._actid = actid
        self._aname = name
        self._color = color
        self._type = atype
        self._properties = {}
        for (key, value) in properties.items():
            self._properties[str(key)] = str(value)
        self._buddies = {}

        self._object_id = object_id
        self._object_path = _ACTIVITY_PATH + str(self._object_id)
        dbus.service.Object.__init__(self, bus_name, self._object_path)

    def add_buddy(self, buddy):
        if self._buddies.has_key(buddy._key):
            raise NotFoundError("Buddy already in activity")
        self._buddies[buddy._key] = buddy
        self.BuddyJoined(buddy._object_path)

    def remove_buddy(self, buddy):
        if not self._buddies.has_key(buddy._key):
            raise NotFoundError("Buddy not in activity")
        self.BuddyLeft(buddy._object_path)
        del self._buddies[buddy._key]

    def disappear(self):
        # remove all buddies from activity
        for buddy in self.get_buddies():
            self.BuddyLeft(buddy._object_path)
        self._buddies = {}

    def get_buddies(self):
        return self._buddies.values()

    @dbus.service.signal(_ACTIVITY_INTERFACE, signature="o")
    def BuddyJoined(self, buddy_path):
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE, signature="o")
    def BuddyLeft(self, buddy_path):
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE, signature="o")
    def NewChannel(self, channel_path):
        pass

    @dbus.service.method(_ACTIVITY_INTERFACE, out_signature="s")
    def GetId(self):
        return self._actid

    @dbus.service.method(_ACTIVITY_INTERFACE, out_signature="s")
    def GetName(self):
        return self._aname

    @dbus.service.method(_ACTIVITY_INTERFACE, out_signature="s")
    def GetColor(self):
        return self._color

    @dbus.service.method(_ACTIVITY_INTERFACE, out_signature="s")
    def GetType(self):
        return self._type

    @dbus.service.method(_ACTIVITY_INTERFACE)
    def Join(self):
        owner = self._parent._owner
        self.add_buddy(owner)
        owner.add_activity(self)

    @dbus.service.method(_ACTIVITY_INTERFACE, out_signature="ao")
    def GetJoinedBuddies(self):
        ret = []
        for buddy in self._buddies.values():
            ret.append(dbus.ObjectPath(buddy._object_path))
        return ret

    @dbus.service.method(_ACTIVITY_INTERFACE, out_signature="soao")
    def GetChannels(self):
        return None


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

    def add_activity(self, activity):
        if self._activities.has_key(activity._actid):
            raise NotFoundError("Buddy already in activity")
        self._activities[activity._actid] = activity
        self.JoinedActivity(activity._object_path)

    def remove_activity(self, activity):
        if not self._activities.has_key(activity._actid):
            raise NotFoundError("Buddy not in activity")
        self.LeftActivity(activity._object_path)
        del self._activities[activity._actid]

    def leave_activities(self):
        for activity in self.get_activities():
            self.LeftActivity(activity._object_path)
        self._activities = {}

    def get_activities(self):
        return self._activities.values()

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
_PRESENCE_TEST_INTERFACE = "org.laptop.Sugar.Presence._Test"
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

    def _internal_share_activity(self, actid, atype, name, properties, color=None):
        objid = self._get_next_object_id()
        if not color:
            color = self._owner._color
        act = TestActivity(self._bus_name, objid, self, actid, name, color, atype, properties)
        self._activities[actid] = act
        self.ActivityAppeared(act._object_path)
        return act

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="sssa{sv}",
            out_signature="o")
    def ShareActivity(self, actid, atype, name, properties):
        act = self._internal_share_activity(actid, atype, name, properties)
        act.add_buddy(self._owner)
        self._owner.add_activity(act)
        return act._object_path

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="so")
    def GetPreferredConnection(self):
        return "bar.baz.foo", "/bar/baz/foo"

    # Private methods used for testing
    @dbus.service.method(_PRESENCE_TEST_INTERFACE, in_signature="ayss")
    def AddBuddy(self, pubkey, nick, color):
        pubkey = ''.join([chr(item) for item in pubkey])
        objid = self._get_next_object_id()
        buddy = TestBuddy(self._bus_name, objid, pubkey, nick, color)
        self._buddies[pubkey] = buddy
        self.BuddyAppeared(buddy._object_path)

    @dbus.service.method(_PRESENCE_TEST_INTERFACE, in_signature="ay")
    def RemoveBuddy(self, pubkey):
        pubkey = ''.join([chr(item) for item in pubkey])
        if not self._buddies.has_key(pubkey):
            raise NotFoundError("Buddy not found")
        buddy = self._buddies[pubkey]
        activities = buddy.get_activities()
        # remove activity from the buddy
        buddy.leave_activities()
        # remove the buddy from all activities
        for act in activities:
            act.remove_buddy(buddy)
        self.BuddyDisappeared(buddy._object_path)
        del self._buddies[pubkey]

    @dbus.service.method(_PRESENCE_TEST_INTERFACE, in_signature="oo")
    def AddBuddyToActivity(self, pubkey, actid):
        pubkey = ''.join([chr(item) for item in pubkey])
        if not self._buddies.has_key(pubkey):
            raise NotFoundError("Buddy unknown")
        if not self._activities.has_key(actid):
            raise NotFoundError("Activity unknown")

        buddy = self._buddies[pubkey]
        activity = self._activities[actid]
        activity.add_buddy(buddy)
        buddy.add_activity(activity)

    @dbus.service.method(_PRESENCE_TEST_INTERFACE, in_signature="oo")
    def RemoveBuddyFromActivity(self, pubkey, actid):
        pubkey = ''.join([chr(item) for item in pubkey])
        if not self._buddies.has_key(pubkey):
            raise NotFoundError("Buddy unknown")
        if not self._activities.has_key(actid):
            raise NotFoundError("Activity unknown")

        buddy = self._buddies[pubkey]
        activity = self._activities[actid]
        buddy.remove_activity(activity)
        activity.remove_buddy(buddy)

    @dbus.service.method(_PRESENCE_TEST_INTERFACE, in_signature="ssssa{sv}")
    def AddActivity(self, actid, name, color, atype, properties):
        self._internal_share_activity(actid, atype, name, properties, color=color)

    @dbus.service.method(_PRESENCE_TEST_INTERFACE, in_signature="s")
    def RemoveActivity(self, actid):
        if not self._activities.has_key(actid):
            raise NotFoundError("Activity not found")
        act = self._activities[actid]
        # remove activity from all buddies
        for buddy in act.get_buddies():
            buddy.remove_activity(act)
        act.disappear()
        self.ActivityDisappeared(act._object_path)
        del self._activities[actid]

def main():
    import logging
    logging.basicConfig(level=logging.DEBUG)

    loop = gobject.MainLoop()
    ps = TestPresenceService()
    loop.run()

if __name__ == "__main__":
    main()
