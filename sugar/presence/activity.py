"""UI interface to an activity in the presence service"""
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
    """UI interface for an Activity in the presence service
    
    Activities in the presence service represent other user's
    shared activities and your own activities (XXX shared or 
    otherwise?)
    
    Properties:
        id 
        color 
        name 
        type 
        joined 
    """
    __gsignals__ = {
        'buddy-joined': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'buddy-left':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'new-channel':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'joined':       (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }

    __gproperties__ = {
        'id'        : (str, None, None, None, gobject.PARAM_READABLE),
        'name'      : (str, None, None, None, gobject.PARAM_READABLE),
        'color'     : (str, None, None, None, gobject.PARAM_READABLE),
        'type'      : (str, None, None, None, gobject.PARAM_READABLE),
        'joined'    : (bool, None, None, False, gobject.PARAM_READABLE)
    }

    _PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
    _ACTIVITY_DBUS_INTERFACE = "org.laptop.Sugar.Presence.Activity"

    def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
        """Initialse the activity interface, connecting to service"""
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
        """Get our dbus object path"""
        return self._object_path

    def do_get_property(self, pspec):
        """Retrieve a particular property from our property dictionary"""
        if pspec.name == "id":
            if not self._id:
                self._id = self._activity.GetId()
            return self._id
        elif pspec.name == "name":
            if not self._name:
                self._name = self._activity.GetName()
            return self._name
        elif pspec.name == "color":
            if not self._color:
                self._color = self._activity.GetColor()
            return self._color
        elif pspec.name == "type":
            if not self._type:
                self._type = self._activity.GetType()
            return self._type
        elif pspec.name == "joined":
            return self._joined

    def _emit_buddy_joined_signal(self, object_path):
        """Generate buddy-joined GObject signal with presence Buddy object"""
        self.emit('buddy-joined', self._ps_new_object(object_path))
        return False

    def _buddy_joined_cb(self, object_path):
        gobject.idle_add(self._emit_buddy_joined_signal, object_path)

    def _emit_buddy_left_signal(self, object_path):
        """Generate buddy-left GObject signal with presence Buddy object
        
        XXX note use of _ps_new_object instead of _ps_del_object here
        """
        self.emit('buddy-left', self._ps_new_object(object_path))
        return False

    def _buddy_left_cb(self, object_path):
        gobject.idle_add(self._emit_buddy_left_signal, object_path)

    def _emit_new_channel_signal(self, object_path):
        """Generate new-channel GObject signal with channel object path 
        
        New telepathy-python communications channel has been opened
        """
        self.emit('new-channel', object_path)
        return False

    def _new_channel_cb(self, object_path):
        gobject.idle_add(self._emit_new_channel_signal, object_path)

    def get_joined_buddies(self):
        """Retrieve the set of Buddy objects attached to this activity
        
        returns list of presence Buddy objects
        """
        resp = self._activity.GetJoinedBuddies()
        buddies = []
        for item in resp:
            buddies.append(self._ps_new_object(item))
        return buddies

    def _join_cb(self):
        self._joined = True
        self.emit("joined", True, None)

    def _join_error_cb(self, err):
        self.emit("joined", False, str(err))

    def join(self):
        """Join this activity 
        
        XXX if these are all activities, can I join my own activity?
        """
        if self._joined:
            self.emit("joined", True, None)
            return
        self._activity.Join(reply_handler=self._join_cb, error_handler=self._join_error_cb)

    def get_channels(self):
        """Retrieve communications channel descriptions for the activity 
        
        Returns (bus name, connection, channels) for the activity
        
        XXX what are those values?
        """
        (bus_name, connection, channels) = self._activity.GetChannels()
        return bus_name, connection, channels

    def leave(self):
        # FIXME
        self._joined = False
