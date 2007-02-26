# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007, Collabora Ltd.
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
import dbus, dbus.service
from sugar import profile

_BUDDY_PATH = "/org/laptop/Sugar/Presence/Buddies/"
_BUDDY_INTERFACE = "org.laptop.Sugar.Presence.Buddy"
_OWNER_INTERFACE = "org.laptop.Sugar.Presence.Buddy.Owner"

class NotFoundError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'

class Buddy(dbus.service.Object):
    """Represents another person on the network and keeps track of the
    activities and resources they make available for sharing."""

    def __init__(self, bus_name, object_id, icon_cache, handle=None):
        if not bus_name:
            raise ValueError("DBus bus name must be valid")
        if not object_id or not isinstance(object_id, int):
            raise ValueError("object id must be a valid number")

        self._bus_name = bus_name
        self._object_id = object_id
        self._object_path = _BUDDY_PATH + str(self._object_id)

        dbus.service.Object.__init__(self, self._bus_name, self._object_path)

        self._activities = {}   # Activity ID -> Activity

        self._icon_cache = icon_cache

        self.handles = {} # tp client -> handle

        self._nick_name = None
        self._color = None
        self._key = None
        self._current_activity = None

    # dbus signals
    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="ay")
    def IconChanged(self, icon_data):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="o")
    def JoinedActivity(self, activity_path):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="o")
    def LeftActivity(self, activity_path):
        pass

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="a{sv}")
    def PropertyChanged(self, updated):
        pass

    # dbus methods
    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="ay")
    def GetIcon(self):
        icon = self.get_icon()
        if not icon:
            return ""
        return icon

    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedActivities(self):
        acts = []
        for act in self.get_joined_activities():
            acts.append(act.object_path())
        return acts

    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="a{sv}")
    def GetProperties(self):
        props = {}
        props['name'] = self.get_name()
        props['owner'] = self.is_owner()
        props['key'] = self.get_key()
        color = self.get_color()
        if color:
            props['color'] = color
        return props

    # methods
    def object_path(self):
        return dbus.ObjectPath(self._object_path)

    def add_activity(self, activity):
        actid = activity.get_id()
        if self._activities.has_key(actid):
            return
        self._activities[actid] = activity
        if activity.is_valid():
            self.JoinedActivity(activity.object_path())

    def remove_activity(self, activity):
        actid = activity.get_id()
        if not self._activities.has_key(actid):
            return
        del self._activities[actid]
        if activity.is_valid():
            self.LeftActivity(activity.object_path())

    def get_joined_activities(self):
        acts = []
        for act in self._activities.values():
            if act.is_valid():
                acts.append(act)
        return acts

    def get_icon(self):
        """Return the buddies icon, if any."""
        return self._icon
        
    def get_name(self):
        return self._nick_name

    def get_color(self):
        return self._color

    def get_current_activity(self):
        if not self._current_activity:
            return None
        if not self._activities.has_key(self._current_activity):
            return None
        return self._activities[self._current_activity]

    def _set_icon(self, icon):
        """Can only set icon for other buddies.  The Owner
        takes care of setting it's own icon."""
        if icon != self._icon:
            self._icon = icon
            self.IconChanged(icon)

    def _set_name(self, name):
        self._nick_name = name

    def _set_color(self, color):
        self._color = color

    def set_properties(self, prop):
        if "name" in properties.keys():
            self._set_name(properties["name"])
        if "color" in properties.keys():
            self._set_color(properties["color"])
        self.PropertyChanged(properties)

    def is_owner(self):
        return False

    def set_key(self, key):
        self._key = key

    def get_key(self):
        return self._key

class Owner(Buddy):
    """Class representing the owner of the machine.  This is the client
    portion of the Owner, paired with the server portion in Owner.py."""
    def __init__(self, ps, bus_name, object_id, icon_cache):
        Buddy.__init__(self, bus_name, object_id, icon_cache)

        self._ps = ps
        self._nick_name = profile.get_nick_name()
        self._color = profile.get_color().to_string()
        self._key = profile.get_pubkey()

    # dbus methods
    @dbus.service.method(_OWNER_INTERFACE,
                        in_signature="ay", out_signature="")
    def SetIcon(self, icon_data):
        self.set_icon(icon_data)

    @dbus.service.method(_OWNER_INTERFACE,
                        in_signature="a{sv}", out_signature="")
    def SetProperties(self, prop):
        self.set_properties(self, prop)

    # methods
    def is_owner(self):
        return True

    def set_icon(self, icon):
        self._icon = icon

