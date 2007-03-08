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
from telepathy.client import ManagerRegistry, Connection
from telepathy.interfaces import (CONN_MGR_INTERFACE, CONN_INTERFACE)
from telepathy.constants import (CONNECTION_STATUS_CONNECTING, CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_DISCONNECTED, CONNECTION_HANDLE_TYPE_CONTACT)
 
from server_plugin import ServerPlugin
from linklocal_plugin import LinkLocalPlugin

from buddy import Buddy, Owner
from activity import Activity

_PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
_PRESENCE_INTERFACE = "org.laptop.Sugar.Presence"
_PRESENCE_PATH = "/org/laptop/Sugar/Presence"


class NotFoundError(dbus.DBusException):
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'


class PresenceService(dbus.service.Object):
    def __init__(self):
        self._next_object_id = 0

        self._buddies = {}      # key -> Buddy
        self._handles_buddies = {}      # tp client -> (handle -> Buddy)
        self._activities = {}   # activity id -> Activity

        bus = dbus.SessionBus()
        self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE, bus=bus)        

        # Create the Owner object
        objid = self._get_next_object_id()
        self._owner = Owner(self._bus_name, objid)
        self._buddies[self._owner.props.key] = self._owner

        self._registry = ManagerRegistry()
        self._registry.LoadManagers()

        # Set up the server connection
        self._server_plugin = ServerPlugin(self._registry)
        self._handles_buddies[self._server_plugin] = {}

        self._server_plugin.connect('status', self._server_status_cb)
        self._server_plugin.connect('contact-online', self._contact_online)
        self._server_plugin.connect('contact-offline', self._contact_offline)
        self._server_plugin.connect('avatar-updated', self._avatar_updated)
        self._server_plugin.connect('properties-changed', self._properties_changed)
        self._server_plugin.connect('contact-activities-changed', self._contact_activities_changed)
        self._server_plugin.connect('activity-invitation', self._activity_invitation)
        self._server_plugin.connect('private-invitation', self._private_invitation)
        self._server_plugin.start()

        # Set up the link local connection
        self._ll_plugin = LinkLocalPlugin(self._registry)
        self._handles_buddies[self._ll_plugin] = {}

        dbus.service.Object.__init__(self, self._bus_name, _PRESENCE_PATH)

    def _server_status_cb(self, plugin, status, reason):
        if status == CONNECTION_STATUS_CONNECTED:
            pass

    def _contact_online(self, tp, handle, props):
        new_buddy = False
        key = props['key']
        buddy = self._buddies.get(key)
        if not buddy:
            # we don't know yet this buddy
            objid = self._get_next_object_id()
            buddy = Buddy(self._bus_name, objid, key=key)
            buddy.connect("validity-changed", self._buddy_validity_changed_cb)
            self._buddies[key] = buddy

        buddies = self._handles_buddies[tp]
        buddies[handle] = buddy
        # store the handle of the buddy for this CM
        buddy.handles[tp] = handle

        buddy.set_properties(props)

    def _buddy_validity_changed_cb(self, buddy, valid):
        if valid:
            self.BuddyAppeared(buddy.object_path())
            print "New Buddy: %s (%s)" % (buddy.props.nick, buddy.props.color)
        else:
            self.BuddyDisappeared(buddy.object_path())
            print "Buddy left: %s (%s)" % (buddy.props.nick, buddy.props.color)
            
    def _contact_offline(self, tp, handle):
        buddy = self._handles_buddies[tp].pop(handle)
        key = buddy.props.key

        # the handle of the buddy for this CM is not valid anymore
        buddy.handles.pop(tp)
        if not buddy.handles:
            if buddy.props.valid:
                self.BuddyDisappeared(buddy.object_path())
                print "Buddy left: %s (%s)" % (buddy.props.nick, buddy.props.color)
            self._buddies.pop(key)

    def _get_next_object_id(self):
        """Increment and return the object ID counter."""
        self._next_object_id = self._next_object_id + 1
        return self._next_object_id

    def _avatar_updated(self, tp, handle, avatar):
        buddy = self._handles_buddies[tp].get(handle)
        if buddy and not buddy.props.owner:
            print "Buddy %s icon updated" % buddy.props.key
            buddy.props.icon = avatar

    def _properties_changed(self, tp, handle, prop):
        buddy = self._handles_buddies[tp].get(handle)
        if buddy:
            buddy.set_properties(prop)
            #print "Buddy %s properties updated" % buddy.props.key

    def _new_activity(self, activity_id, tp):
        objid = self._get_next_object_id()
        activity = Activity(self._bus_name, objid, activity_id, tp)
        # FIXME : don't do that shit !
        activity._valid = True
        self._activities[activity_id] = activity

        print "new activity", activity_id
        self.ActivityAppeared(activity.object_path())

        return activity

    def _remove_activity(self, activity):
        print "remove activity", activity.get_id()

        self.ActivityDisappeared(activity.object_path())
        del self._activities[activity.get_id()]
    
    def _contact_activities_changed(self, tp, contact_handle, activities):
        print "------------activities changed-------------"
        buddies = self._handles_buddies[tp]
        buddy = buddies.get(contact_handle)

        if not buddy:
            # We don't know this buddy
            # FIXME: What should we do here? 
            # FIXME: Do we need to check if the buddy is valid or something?
            print "contact_activities_changed: buddy unknow"
            return

        old_activities = set()
        for activity in buddy.get_joined_activities():
            old_activities.add(activity.get_id())

        new_activities = set(activities)

        activities_joined = new_activities - old_activities
        for act in activities_joined:
            print "buddy", contact_handle, "joined", act
            activity = self._activities.get(act)
            if not activity:
                # new activity
                activity = self._new_activity(act, tp)

            activity.buddy_joined(buddy)
            buddy.add_activity(activity)

        activities_left = old_activities - new_activities
        for act in activities_left:
            print "buddy", contact_handle, "left", act
            activity = self._activities.get(act)
            if not activity:
                continue
            
            activity.buddy_left(buddy)
            buddy.remove_activity(activity)

            if not activity.get_joined_buddies():
                self._remove_activity(activity)

        # current activity
        if len(activities) > 0:
            buddy.set_properties({'current-activity':activities[0]})

    def _activity_invitation(self, tp, act_id):
        activity = self._activities.get(act_id)
        if activity:
            self.ActivityInvitation(activity.object_path())

    def _private_invitation(self, tp, chan_path):
        conn = tp.get_connection()
        self.PrivateInvitation(str(conn.service_name), conn.object_path, chan_path)

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
            ret.append(act.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="s", out_signature="o")
    def GetActivityById(self, actid):
        if self._activities.has_key(actid):
            return self._activities[actid].object_path()
        raise NotFoundError("The activity was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetBuddies(self):
        ret = []
        for buddy in self._buddies.values():
            ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="ay", out_signature="o")
    def GetBuddyByPublicKey(self, key):
        if self._buddies.has_key(key):
            return self._buddies[key].object_path()
        raise NotFoundError("The buddy was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="o")
    def GetOwner(self):
        if not self._owner:
            raise NotFoundError("The owner was not found.")
        else:
            return self._owner.get_object_path()

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="sssa{sv}", out_signature="o")
    def ShareActivity(self, actid, atype, name, properties):
        activity = self._share_activity(actid, atype, name, properties)
        return activity.object_path()

    def cleanup(self):
        for tp in self._handles_buddies:
            tp.cleanup()

    def _share_activity(self, actid, atype, name, properties):
        objid = self._get_next_object_id()
        # FIXME check which tp client we should use to share the activity
        activity = Activity(self._bus_name, objid, actid, self._server_plugin)
        # FIXME : don't do that shit !
        activity._valid = True
        self._activities[actid] = activity
        # FIXME set the type, name, properties...

        print "new activity", actid
        activity.join()
        self.ActivityAppeared(activity.object_path())

        return activity


def main():
    loop = gobject.MainLoop()
    ps = PresenceService()
    try:
        loop.run()
    except KeyboardInterrupt:
        ps.cleanup()
        print 'Ctrl+C pressed, exiting...'

if __name__ == "__main__":
    main()
