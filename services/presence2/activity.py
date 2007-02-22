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

import dbus, dbus.service

_ACTIVITY_PATH = "/org/laptop/Sugar/Presence/Activities/"
_ACTIVITY_INTERFACE = "org.laptop.Sugar.Presence.Activity"

class Activity(dbus.service.Object):
    def __init__(self, bus_name, object_id):
        self._buddies = []
        self._color = None
        self._valid = False
        self._activity_id = None

        self._object_id = object_id
        self._object_path = "/org/laptop/Presence/Activities/%d" % self._object_id

        dbus.service.Object.__init__(self, bus_name, self._object_path)
        

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
        return self.get_id()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetColor(self):
        return self.get_color()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="")
    def Join(self):
        raise NotImplementedError("not implemented yet")

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedBuddies(self):
        for buddy in self._buddies:
            ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="soao")
    def GetChannels(self):
        raise NotImplementedError("not implemented yet")

    # methods
    def object_path(self):
        return dbus.ObjectPath(self._object_path)

    def is_valid(self):
        """An activity is only valid when it's color is available."""
        return self._valid

    def get_id(self):
        return self._activity_id

    def get_color(self):
        return self._color
