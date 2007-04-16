"""UI class to access system-level presence object"""
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

import dbus, dbus.glib, gobject
import logging

# XXX use absolute imports
#   from sugar.presence import buddy, activity
# this *kind* of relative import is deprecated
# with an explicit relative import slated to be 
# introduced (available in Python 2.5 with a __future__
# import), that would read as:
#   from . import buddy, activity 
# see PEP: http://docs.python.org/whatsnew/pep-328.html
import buddy, activity

class ObjectCache(object):
    """Path to Activity/Buddy object cache
    
    On notification of a new object of either type the 
    PresenceService client stores the object's representation
    in this object.
    
    XXX Why not just sub-class dict?  We're only adding two
        methods then and we would have all of the other 
        standard operations on dictionaries.
    """
    def __init__(self):
        """Initialise the cache"""
        self._cache = {}

    def get(self, object_path):
        """Retrieve specified object from the cache 
        
        object_path -- full dbus path to the object
        
        returns a presence.buddy.Buddy or presence.activity.Activity
        instance or None if the object_path is not yet cached.
        
        XXX could be written as return self._cache.get( object_path )
        """
        try:
            return self._cache[object_path]
        except KeyError:
            return None

    def add(self, obj):
        """Adds given presence object to the cache 
        
        obj -- presence Buddy or Activity representation, the object's
            object_path() method is used as the key for storage
        
        returns None 
        
        XXX should raise an error on collisions, shouldn't it? or 
            return True/False to say whether the item was actually
            added
        """
        op = obj.object_path()
        if not self._cache.has_key(op):
            self._cache[op] = obj

    def remove(self, object_path):
        """Remove the given presence object from the cache 
        
        object_path -- full dbus path to the object
        
        returns None 
        
        XXX does two checks instead of one with a try:except for the 
            keyerror, normal case of deleting existing penalised as
            a result.
            
            try:
                return self._cache.pop( key )
            except KeyError:
                return None
        """
        if self._cache.has_key(object_path):
            del self._cache[object_path]


DBUS_SERVICE = "org.laptop.Sugar.Presence"
DBUS_INTERFACE = "org.laptop.Sugar.Presence"
DBUS_PATH = "/org/laptop/Sugar/Presence"


class PresenceService(gobject.GObject):
    """UI-side interface to the dbus presence service 
    
    This class provides UI programmers with simplified access
    to the dbus service of the same name.  It allows for observing
    various events from the presence service as GObject events,
    as well as some basic introspection queries.
    """
    __gsignals__ = {
        'buddy-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'buddy-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'activity-invitation': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'private-invitation': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                          gobject.TYPE_PYOBJECT])),
        'activity-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'activity-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'activity-shared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                          gobject.TYPE_PYOBJECT]))
    }

    _PS_BUDDY_OP = DBUS_PATH + "/Buddies/"
    _PS_ACTIVITY_OP = DBUS_PATH + "/Activities/"
    

    def __init__(self):
        """Initialise the service and connect to events"""
        gobject.GObject.__init__(self)
        self._objcache = ObjectCache()
        self._bus = dbus.SessionBus()
        self._ps = dbus.Interface(self._bus.get_object(DBUS_SERVICE,
                DBUS_PATH), DBUS_INTERFACE)
        self._ps.connect_to_signal('BuddyAppeared', self._buddy_appeared_cb)
        self._ps.connect_to_signal('BuddyDisappeared', self._buddy_disappeared_cb)
        self._ps.connect_to_signal('ActivityAppeared', self._activity_appeared_cb)
        self._ps.connect_to_signal('ActivityDisappeared', self._activity_disappeared_cb)
        self._ps.connect_to_signal('ActivityInvitation', self._activity_invitation_cb)
        self._ps.connect_to_signal('PrivateInvitation', self._private_invitation_cb)

    def _new_object(self, object_path):
        """Turn new object path into (cached) Buddy/Activity instance
        
        object_path -- full dbus path of the new object, must be
            prefixed with either of _PS_BUDDY_OP or _PS_ACTIVITY_OP
        
        Note that this method is called throughout the class whenever
        the representation of the object is required, it is not only 
        called when the object is first discovered.
        
        returns presence Buddy or Activity representation
        """
        obj = self._objcache.get(object_path)
        if not obj:
            if object_path.startswith(self._PS_BUDDY_OP):
                obj = buddy.Buddy(self._bus, self._new_object,
                        self._del_object, object_path)
            elif object_path.startswith(self._PS_ACTIVITY_OP):
                obj = activity.Activity(self._bus, self._new_object,
                        self._del_object, object_path)
            else:
                raise RuntimeError("Unknown object type")
            self._objcache.add(obj)
        return obj

    def _del_object(self, object_path):
        # FIXME
        pass

    def _emit_buddy_appeared_signal(self, object_path):
        """Emit GObject event with presence.buddy.Buddy object"""
        self.emit('buddy-appeared', self._new_object(object_path))
        return False

    def _buddy_appeared_cb(self, op):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_buddy_appeared_signal, op)

    def _emit_buddy_disappeared_signal(self, object_path):
        """Emit GObject event with presence.buddy.Buddy object"""
        self.emit('buddy-disappeared', self._new_object(object_path))
        return False

    def _buddy_disappeared_cb(self, object_path):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_buddy_disappeared_signal, object_path)

    def _emit_activity_invitation_signal(self, object_path):
        """Emit GObject event with presence.activity.Activity object"""
        self.emit('activity-invitation', self._new_object(object_path))
        return False

    def _activity_invitation_cb(self, object_path):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_activity_invitation_signal, object_path)

    def _emit_private_invitation_signal(self, bus_name, connection, channel):
        """Emit GObject event with bus_name, connection and channel
        
        XXX This seems to generate the wrong GObject event?  It generates 
            'service-disappeared' instead of private-invitation for some 
            reason.  That event doesn't even seem to be registered?
        """
        self.emit('service-disappeared', bus_name, connection, channel)
        return False

    def _private_invitation_cb(self, bus_name, connection, channel):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_service_disappeared_signal, bus_name,
                connection, channel)

    def _emit_activity_appeared_signal(self, object_path):
        """Emit GObject event with presence.activity.Activity object"""
        self.emit('activity-appeared', self._new_object(object_path))
        return False

    def _activity_appeared_cb(self, object_path):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_activity_appeared_signal, object_path)

    def _emit_activity_disappeared_signal(self, object_path):
        """Emit GObject event with presence.activity.Activity object"""
        self.emit('activity-disappeared', self._new_object(object_path))
        return False

    def _activity_disappeared_cb(self, object_path):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_activity_disappeared_signal, object_path)

    def get(self, object_path):
        """Retrieve given object path as a Buddy/Activity object
        
        XXX This is basically just an alias for _new_object, i.e. it 
            just adds an extra function-call to the operation.
        """
        return self._new_object(object_path)

    def get_activities(self):
        """Retrieve set of all activities from service
        
        returns list of Activity objects for all object paths
            the service reports exist (using GetActivities)
        """
        resp = self._ps.GetActivities()
        acts = []
        for item in resp:
            acts.append(self._new_object(item))
        return acts

    def get_activity(self, activity_id):
        """Retrieve single Activity object for the given unique id 
        
        activity_id -- unique ID for the activity 
        
        returns single Activity object or None if the activity 
            is not found using GetActivityById on the service
        """
        try:
            act_op = self._ps.GetActivityById(activity_id)
        except dbus.exceptions.DBusException:
            return None
        return self._new_object(act_op)

    def get_buddies(self):
        """Retrieve set of all buddies from service
        
        returns list of Buddy objects for all object paths
            the service reports exist (using GetBuddies)
        """
        resp = self._ps.GetBuddies()
        buddies = []
        for item in resp:
            buddies.append(self._new_object(item))
        return buddies

    def get_buddy(self, key):
        """Retrieve single Buddy object for the given public key
        
        key -- buddy's public encryption key
        
        returns single Buddy object or None if the activity 
            is not found using GetBuddyByPublicKey on the 
            service
        """
        try:
            buddy_op = self._ps.GetBuddyByPublicKey(dbus.ByteArray(key))
        except dbus.exceptions.DBusException:
            return None
        return self._new_object(buddy_op)

    def get_owner(self):
        """Retrieves "owner" as a Buddy
        
        XXX check that it really is a Buddy that's produced, what is 
            this the owner of?  Shouldn't it be getting an activity 
            and then asking who the owner of that is?
        """
        try:
            owner_op = self._ps.GetOwner()
        except dbus.exceptions.DBusException:
            return None
        return self._new_object(owner_op)

    def _share_activity_cb(self, activity, op):
        """Notify with GObject event of successful sharing of activity"""
        self.emit("activity-shared", True, self._new_object(op), None)

    def _share_activity_error_cb(self, activity, err):
        """Notify with GObject event of unsuccessful sharing of activity"""
        logging.debug("Error sharing activity %s: %s" % (activity.get_id(), err))
        self.emit("activity-shared", False, None, err)

    def share_activity(self, activity, properties={}):
        """Ask presence service to ask the activity to share itself
        
        Uses the ShareActivity method on the service to ask for the 
        sharing of the given activity.  Arranges to emit activity-shared 
        event with:
        
            (success, Activity, err)
        
        on success/failure.
        
        returns None
        """
        actid = activity.get_id()
        atype = activity.get_service_name()
        name = activity.props.title
        self._ps.ShareActivity(actid, atype, name, properties,
                reply_handler=lambda *args: self._share_activity_cb(activity, *args),
                error_handler=lambda *args: self._share_activity_error_cb(activity, *args))

    def get_preferred_connection(self):
        """Gets the preferred telepathy connection object that an activity
        should use when talking directly to telepathy

        returns the bus name and the object path of the Telepathy connection"""

        try:
            bus_name, object_path = self._ps.GetPreferredConnection()
        except dbus.exceptions.DBusException:
            return None

        return bus_name, object_path


class _MockPresenceService(gobject.GObject):
    """Test fixture allowing testing of items that use PresenceService
    
    See PresenceService for usage and purpose
    """
    __gsignals__ = {
        'buddy-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'buddy-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'activity-invitation': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'private-invitation': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                          gobject.TYPE_PYOBJECT])),
        'activity-appeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT])),
        'activity-disappeared': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                        ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

    def get_activities(self):
        return []

    def get_activity(self, activity_id):
        return None

    def get_buddies(self):
        return []

    def get_buddy(self, key):
        return None

    def get_owner(self):
        return None

    def share_activity(self, activity, properties={}):
        return None

_ps = None
def get_instance():
    """Retrieve this process' view of the PresenceService"""
    global _ps
    if not _ps:
        _ps = PresenceService()
    return _ps

