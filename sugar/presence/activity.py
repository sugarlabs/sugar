# Copyright (C) 2007, Red Hat, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gobject
import dbus

class Activity(gobject.GObject):

    __gsignals__ = {
        'buddy-joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'buddy-left': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'new-channel': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT]))
    }

    _PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
    _ACTIVITY_DBUS_INTERFACE = "org.laptop.Sugar.Presence.Activity"

    def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
        gobject.GObject.__init__(self)
        self._object_path = object_path
        self._ps_new_object = new_obj_cb
        self._ps_del_object = del_obj_cb
        bobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
        self._activity = dbus.Interface(bobj, self._ACTIVITY_DBUS_INTERFACE)
        self._activity.connect_to_signal('BuddyJoined', self._buddy_joined_cb)
        self._activity.connect_to_signal('BuddyLeft', self._buddy_left_cb)
        self._activity.connect_to_signal('NewChannel', self._new_channel_cb)

        self._id = None
        self._color = None
        self._name = None
        self._type = None
        self._joined = False

    def object_path(self):
        return self._object_path

    def _emit_buddy_joined_signal(self, object_path):
        self.emit('buddy-joined', self._ps_new_object(object_path))
        return False

    def _buddy_joined_cb(self, object_path):
        gobject.idle_add(self._emit_buddy_joined_signal, object_path)

    def _emit_buddy_left_signal(self, object_path):
        self.emit('buddy-left', self._ps_new_object(object_path))
        return False

    def _buddy_left_cb(self, object_path):
        gobject.idle_add(self._emit_buddy_left_signal, object_path)

    def _emit_new_channel_signal(self, object_path):
        self.emit('new-channel', object_path)
        return False

    def _new_channel_cb(self, object_path):
        gobject.idle_add(self._emit_new_channel_signal, object_path)

    def get_id(self):
        # Cache activity ID, which should never change anyway
        if not self._id:
            self._id = self._activity.GetId()
        return self._id

    def get_color(self):
        if not self._color:
            self._color = self._activity.GetColor()
        return self._color

    def get_name(self):
        if not self._name:
            self._name = self._activity.GetName()
        return self._name

    def get_type(self):
        if not self._type:
            self._type = self._activity.GetType()
        return self._type

    def get_joined_buddies(self):
        resp = self._activity.GetJoinedBuddies()
        buddies = []
        for item in resp:
            buddies.append(self._ps_new_object(item))
        return buddies

    def join(self):
        if self._joined:
            return
        self._activity.Join()
        self._joined = True

    def get_channels(self):
        (bus_name, connection, channels) = self._activity.GetChannels()
        return bus_name, connection, channels

    def owner_has_joined(self):
        # FIXME
        return False
