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

from telepathy.interfaces import (CHANNEL_INTERFACE)

_ACTIVITY_PATH = "/org/laptop/Sugar/Presence/Activities/"
_ACTIVITY_INTERFACE = "org.laptop.Sugar.Presence.Activity"

class Activity(dbus.service.Object):
    def __init__(self, bus_name, object_id, activity_id, tp):
        self._buddies = []
        self._color = None
        self._valid = False
        self._name = None
        self._activity_id = activity_id

        self._object_id = object_id
        self._object_path = "/org/laptop/Presence/Activities/%d" % self._object_id
    
        # the telepathy client
        self._tp = tp
        self._activity_text_channel = None

        self._joined = False

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
        self.join()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedBuddies(self):
        for buddy in self._buddies:
            ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="soao")
    def GetChannels(self):
        return self.get_channels()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetName(self):
        return self.get_name()

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

    def get_joined_buddies(self):
        return self._buddies

    def get_name(self):
        return self._name

    def buddy_joined(self, buddy):
        if buddy not in self._buddies:
            self._buddies.append(buddy)
            self.BuddyJoined(buddy.object_path())

    def buddy_left(self, buddy):
        if buddy in self._buddies:
            self._buddies.remove(buddy)
            self.BuddyLeft(buddy.object_path())

    def join(self):
        if not self._joined:
            self._activity_text_channel = self._tp.join_activity(self._activity_id)
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
