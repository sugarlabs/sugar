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
from sugar import util

from telepathy.interfaces import (CHANNEL_INTERFACE)

_ACTIVITY_PATH = "/org/laptop/Sugar/Presence/Activities/"
_ACTIVITY_INTERFACE = "org.laptop.Sugar.Presence.Activity"

class DBusGObjectMetaclass(dbus.service.InterfaceType, gobject.GObjectMeta): pass
class DBusGObject(dbus.service.Object, gobject.GObject): __metaclass__ = DBusGObjectMetaclass


class Activity(DBusGObject):
    __gtype_name__ = "Activity"

    __gsignals__ = {
        'validity-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_BOOLEAN]))
    }

    __gproperties__ = {
        'id'     : (str, None, None, None,
                    gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY),
        'name'   : (str, None, None, None, gobject.PARAM_READWRITE),
        'color'  : (str, None, None, None, gobject.PARAM_READWRITE),
        'type'   : (str, None, None, None, gobject.PARAM_READWRITE),
        'valid'  : (bool, None, None, False, gobject.PARAM_READABLE),
        'local'  : (bool, None, None, False,
                    gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY),
        'joined' : (bool, None, None, False, gobject.PARAM_READABLE)
    }

    def __init__(self, bus_name, object_id, tp, **kwargs):
        if not bus_name:
            raise ValueError("DBus bus name must be valid")
        if not object_id or not isinstance(object_id, int):
            raise ValueError("object id must be a valid number")
        if not tp:
            raise ValueError("telepathy CM must be valid")

        self._object_id = object_id
        self._object_path = _ACTIVITY_PATH + str(self._object_id)
        dbus.service.Object.__init__(self, bus_name, self._object_path)

        self._buddies = []
        self._joined = False

        # the telepathy client
        self._tp = tp
        self._activity_text_channel = None

        self._valid = False
        self._id = None
        self._color = None
        self._local = False
        self._type = None

        if not kwargs.get("id"):
            raise ValueError("activity id is required")
        if not util.validate_activity_id(kwargs['id']):
            raise ValueError("Invalid activity id '%s'" % kwargs['id'])

        gobject.GObject.__init__(self, **kwargs)
        if self.props.local and not self.props.valid:
            raise RuntimeError("local activities require color, type, and name")

    def do_get_property(self, pspec):
        if pspec.name == "id":
            return self._id
        elif pspec.name == "name":
            return self._name
        elif pspec.name == "color":
            return self._color
        elif pspec.name == "type":
            return self._type
        elif pspec.name == "valid":
            return self._valid
        elif pspec.name == "joined":
            return self._joined
        elif pspec.name == "local":
            return self._local

    def do_set_property(self, pspec, value):
        if pspec.name == "id":
            self._id = value
        elif pspec.name == "name":
            self._name = value
        elif pspec.name == "color":
            self._color = value
        elif pspec.name == "type":
            if self._type:
                raise RuntimeError("activity type is already set")
            self._type = value
        elif pspec.name == "joined":
            self._joined = value
        elif pspec.name == "local":
            self._local = value

        self._update_validity()

    def _update_validity(self):
        try:
            old_valid = self._valid
            if self._color and self._name and self._id and self._type:
                self._valid = True
            else:
                self._valid = False

            if old_valid != self._valid:
                self.emit("validity-changed", self._valid)
        except AttributeError:
            self._valid = False

    # dbus signals
    @dbus.service.signal(_ACTIVITY_INTERFACE,
                        signature="o")
    def BuddyJoined(self, buddy_path):
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE,
                        signature="o")
    def BuddyLeft(self, buddy_path):
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE,
                        signature="o")
    def NewChannel(self, channel_path):
        pass

    # dbus methods
    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetId(self):
        return self.props.id

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetColor(self):
        return self.props.color

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetType(self):
        return self.props.type

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="")
    def Join(self):
        self.join()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedBuddies(self):
        ret = []
        for buddy in self._buddies:
            if buddy.props.valid:
                ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="soao")
    def GetChannels(self):
        return self.get_channels()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetName(self):
        return self.props.name

    # methods
    def object_path(self):
        return dbus.ObjectPath(self._object_path)

    def get_joined_buddies(self):
        ret = []
        for buddy in self._buddies:
            if buddy.props.valid:
                ret.append(buddy)
        return ret

    def buddy_joined(self, buddy):
        if buddy not in self._buddies:
            self._buddies.append(buddy)
            if self.props.valid:
                self.BuddyJoined(buddy.object_path())

    def buddy_left(self, buddy):
        if buddy in self._buddies:
            self._buddies.remove(buddy)
            if self.props.valid:
                self.BuddyLeft(buddy.object_path())

    def join(self):
        if not self._joined:
            self._activity_text_channel = self._tp.join_activity(self.props.id)
            self._activity_text_channel[CHANNEL_INTERFACE].connect_to_signal('Closed', self._activity_text_channel_closed_cb)
            self._joined = True

    def get_channels(self):
        conn = self._tp.get_connection()
        # FIXME add tubes and others channels
        return str(conn.service_name), conn.object_path, [self._activity_text_channel.object_path]

    def leave(self):
        if self._joined:
            self._activity_text_channel[CHANNEL_INTERFACE].Close()

    def _activity_text_channel_closed_cb(self):
        self._joined = False
        self._activity_text_channel = None

    def send_properties(self):
        props = {}
        props['name'] = self._name
        props['color'] = self._color
        props['type'] = self._type
        self._tp.set_activity_properties(self.props.id, props)

    def set_properties(self, properties):
        changed  = False
        if "name" in properties.keys():
            name = properties["name"]
            if name != self._name:
                self._name = name
                changed = True

        if "color" in properties.keys():
            color = properties["color"]
            if color != self._color:
                self._color = color
                changed = True

        if "type" in properties.keys():
            type = properties["type"]
            if type != self._type:
                self._type = type
                changed = True

        if changed:
            self._update_validity()
