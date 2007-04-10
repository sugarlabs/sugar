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

import buddy, activity

class ObjectCache(object):
    def __init__(self):
        self._cache = {}

    def get(self, object_path):
        try:
            return self._cache[object_path]
        except KeyError:
            return None

    def add(self, obj):
        op = obj.object_path()
        if not self._cache.has_key(op):
            self._cache[op] = obj

    def remove(self, object_path):
        if self._cache.has_key(object_path):
            del self._cache[object_path]


DBUS_SERVICE = "org.laptop.Sugar.Presence"
DBUS_INTERFACE = "org.laptop.Sugar.Presence"
DBUS_PATH = "/org/laptop/Sugar/Presence"


class PresenceService(gobject.GObject):

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

    _PS_BUDDY_OP = DBUS_PATH + "/Buddies/"
    _PS_ACTIVITY_OP = DBUS_PATH + "/Activities/"
    

    def __init__(self):
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
        self.emit('buddy-appeared', self._new_object(object_path))
        return False

    def _buddy_appeared_cb(self, op):
        gobject.idle_add(self._emit_buddy_appeared_signal, op)

    def _emit_buddy_disappeared_signal(self, object_path):
        self.emit('buddy-disappeared', self._new_object(object_path))
        return False

    def _buddy_disappeared_cb(self, object_path):
        gobject.idle_add(self._emit_buddy_disappeared_signal, object_path)

    def _emit_activity_invitation_signal(self, object_path):
        self.emit('activity-invitation', self._new_object(object_path))
        return False

    def _activity_invitation_cb(self, object_path):
        gobject.idle_add(self._emit_activity_invitation_signal, object_path)

    def _emit_private_invitation_signal(self, bus_name, connection, channel):
        self.emit('service-disappeared', bus_name, connection, channel)
        return False

    def _private_invitation_cb(self, bus_name, connection, channel):
        gobject.idle_add(self._emit_service_disappeared_signal, bus_name,
                connection, channel)

    def _emit_activity_appeared_signal(self, object_path):
        self.emit('activity-appeared', self._new_object(object_path))
        return False

    def _activity_appeared_cb(self, object_path):
        gobject.idle_add(self._emit_activity_appeared_signal, object_path)

    def _emit_activity_disappeared_signal(self, object_path):
        self.emit('activity-disappeared', self._new_object(object_path))
        return False

    def _activity_disappeared_cb(self, object_path):
        gobject.idle_add(self._emit_activity_disappeared_signal, object_path)

    def get(self, object_path):
        return self._new_object(object_path)

    def get_activities(self):
        resp = self._ps.GetActivities()
        acts = []
        for item in resp:
            acts.append(self._new_object(item))
        return acts

    def get_activity(self, activity_id):
        try:
            act_op = self._ps.GetActivityById(activity_id)
        except dbus.exceptions.DBusException:
            return None
        return self._new_object(act_op)

    def get_buddies(self):
        resp = self._ps.GetBuddies()
        buddies = []
        for item in resp:
            buddies.append(self._new_object(item))
        return buddies

    def get_buddy(self, key):
        try:
            buddy_op = self._ps.GetBuddyByPublicKey(dbus.ByteArray(key))
        except dbus.exceptions.DBusException:
            return None
        return self._new_object(buddy_op)

    def get_owner(self):
        try:
            owner_op = self._ps.GetOwner()
        except dbus.exceptions.DBusException:
            return None
        return self._new_object(owner_op)

    def share_activity(self, activity, properties={}):
        actid = activity.get_id()
        atype = activity.get_service_name()
        name = activity.props.title
        serv_op = self._ps.ShareActivity(actid, atype, name, properties)
        return self._new_object(serv_op)


class _MockPresenceService(gobject.GObject):
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
    global _ps
    if not _ps:
        _ps = PresenceService()
    return _ps

