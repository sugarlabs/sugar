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

class DBusGObjectMetaclass(gobject.GObjectMeta, dbus.service.InterfaceType): pass
class DBusGObject(dbus.service.Object, gobject.GObject): __metaclass__ = DBusGObjectMetaclass


class Buddy(DBusGObject):
    """Represents another person on the network and keeps track of the
    activities and resources they make available for sharing."""

    __gtype_name__ = "Buddy"

    __gsignals__ = {
        'validity-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_BOOLEAN]))
    }

    __gproperties__ = {
        'key'              : (str, None, None, None,
                              gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY),
        'icon'             : (str, None, None, None, gobject.PARAM_READWRITE),
        'nick'             : (str, None, None, None, gobject.PARAM_READWRITE),
        'color'            : (str, None, None, None, gobject.PARAM_READWRITE),
        'current-activity' : (str, None, None, None, gobject.PARAM_READWRITE),
        'valid'            : (bool, None, None, False, gobject.PARAM_READABLE),
        'owner'            : (bool, None, None, False, gobject.PARAM_READABLE)
    }

    def __init__(self, bus_name, object_id, **kwargs):
        if not bus_name:
            raise ValueError("DBus bus name must be valid")
        if not object_id or not isinstance(object_id, int):
            raise ValueError("object id must be a valid number")

        self._bus_name = bus_name
        self._object_id = object_id
        self._object_path = _BUDDY_PATH + str(self._object_id)
        dbus.service.Object.__init__(self, self._bus_name, self._object_path)

        self._activities = {}   # Activity ID -> Activity
        self.handles = {} # tp client -> handle

        self._valid = False
        self._owner = False
        self._key = None
        self._icon = ''

        if not kwargs.get("key"):
            raise ValueError("key required")

        gobject.GObject.__init__(self, **kwargs)

    def do_get_property(self, pspec):
        if pspec.name == "key":
            return self._key
        elif pspec.name == "icon":
            return self._icon
        elif pspec.name == "nick":
            return self._nick
        elif pspec.name == "color":
            return self._color
        elif pspec.name == "current-activity":
            if not self._current_activity:
                return None
            if not self._activities.has_key(self._current_activity):
                return None
            return self._activities[self._current_activity]
        elif pspec.name == "valid":
            return self._valid
        elif pspec.name == "owner":
            return self._owner

    def do_set_property(self, pspec, value):
        if pspec.name == "icon":
            if value != self._icon:
                self._icon = value
                self.IconChanged(value)
        elif pspec.name == "nick":
            self._nick = value
        elif pspec.name == "color":
            self._color = value
        elif pspec.name == "current-activity":
            self._current_activity = value
        elif pspec.name == "key":
            self._key = value

        self._update_validity()

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
        if not self.props.icon:
            return ""
        return dbus.ByteArray(self.props.icon)

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
        props['nick'] = self.props.nick
        props['owner'] = self.props.owner
        props['key'] = self.props.key
        props['color'] = self.props.color
        return props

    # methods
    def object_path(self):
        return dbus.ObjectPath(self._object_path)

    def add_activity(self, activity):
        actid = activity.props.id
        if self._activities.has_key(actid):
            return
        self._activities[actid] = activity
        if activity.props.valid:
            self.JoinedActivity(activity.object_path())

    def remove_activity(self, activity):
        actid = activity.props.id
        if not self._activities.has_key(actid):
            return
        del self._activities[actid]
        if activity.props.valid:
            self.LeftActivity(activity.object_path())

    def get_joined_activities(self):
        acts = []
        for act in self._activities.values():
            if act.props.valid:
                acts.append(act)
        return acts

    def set_properties(self, properties):
        if "nick" in properties.keys():
            self._nick = properties["nick"]
        if "color" in properties.keys():
            self._color = properties["color"]

        # Try emitting PropertyChanged before updating validity
        # to avoid leaking a PropertyChanged signal before the buddy is
        # actually valid the first time after creation
        if self._valid:
            self.PropertyChanged(properties)

        self._update_validity()

    def _update_validity(self):
        try:
            old_valid = self._valid
            if self._color and self._nick and self._key:
                self._valid = True
            else:
                self._valid = False

            if old_valid != self._valid:
                self.emit("validity-changed", self._valid)
        except AttributeError:
            self._valid = False


class Owner(Buddy):
    """Class representing the owner of the machine.  This is the client
    portion of the Owner, paired with the server portion in Owner.py."""
    def __init__(self, bus_name, object_id):
        key = profile.get_pubkey()
        nick = profile.get_nick_name()
        color = profile.get_color().to_string()

        Buddy.__init__(self, bus_name, object_id, key=key, nick=nick, color=color)
        self._owner = True

    # dbus methods
    @dbus.service.method(_OWNER_INTERFACE,
                        in_signature="ay", out_signature="")
    def SetIcon(self, icon_data):
        self.props.icon = icon_data

    @dbus.service.method(_OWNER_INTERFACE,
                        in_signature="a{sv}", out_signature="")
    def SetProperties(self, prop):
        self.set_properties(self, prop)

