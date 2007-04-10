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
from sugar import util

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
        self._server_plugin = ServerPlugin(self._registry, self._owner)
        self._handles_buddies[self._server_plugin] = {}

        self._server_plugin.connect('status', self._server_status_cb)
        self._server_plugin.connect('contact-online', self._contact_online)
        self._server_plugin.connect('contact-offline', self._contact_offline)
        self._server_plugin.connect('avatar-updated', self._avatar_updated)
        self._server_plugin.connect('buddy-properties-changed', self._buddy_properties_changed)
        self._server_plugin.connect('buddy-activities-changed', self._buddy_activities_changed)
        self._server_plugin.connect('activity-invitation', self._activity_invitation)
        self._server_plugin.connect('private-invitation', self._private_invitation)
        self._server_plugin.connect('activity-properties-changed', self._activity_properties_changed)
        self._server_plugin.start()

        # Set up the link local connection
        self._ll_plugin = LinkLocalPlugin(self._registry, self._owner)
        self._handles_buddies[self._ll_plugin] = {}

        dbus.service.Object.__init__(self, self._bus_name, _PRESENCE_PATH)

    def _server_status_cb(self, plugin, status, reason):
        if status == CONNECTION_STATUS_CONNECTED:
            pass
            # TEST
            id = util.unique_id()
            self._share_activity(id, "org.laptop.Sugar.Test",
                "Chat of %s" % self._owner.props.nick, [])

    def _contact_online(self, tp, handle, props):
        new_buddy = False
        buddy = self._buddies.get(props["key"])
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

    def _buddy_properties_changed(self, tp, handle, prop):
        buddy = self._handles_buddies[tp].get(handle)
        if buddy:
            buddy.set_properties(prop)
            #print "Buddy %s properties updated" % buddy.props.key

    def _new_activity(self, activity_id, tp):
        try:
            objid = self._get_next_object_id()
            activity = Activity(self._bus_name, objid, tp, id=activity_id)
        except Exception, e:
            print "Invalid activity: %s" % e
            return None

        activity.connect("validity-changed", self._activity_validity_changed_cb)

        self._activities[activity_id] = activity

        # FIXME
        # Use values from the network
        #import random
        #names = ["Tommy", "Susie", "Jill", "Bryan", "Nathan", "Sophia", "Haley", "Jimmy"]
        #name = names[random.randint(0, len(names) - 1)]
        #activity.props.name = "Chat with %s" % name
        #activity.props.type = "org.laptop.Sugar.Chat"
        #from sugar.graphics import xocolor
        #color = xocolor.XoColor().to_string()
        #activity.props.color = color

        return activity

    def _remove_activity(self, activity):
        print "remove activity", activity.props.id

        self.ActivityDisappeared(activity.object_path())
        del self._activities[activity.props.id]
    
    def _buddy_activities_changed(self, tp, contact_handle, activities):
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
            old_activities.add(activity.props.id)

        new_activities = set(activities)

        activities_joined = new_activities - old_activities
        for act in activities_joined:
            print "buddy", contact_handle, "joined", act
            activity = self._activities.get(act)
            if not activity:
                # new activity, can fail
                activity = self._new_activity(act, tp)

            if activity:
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
            if act.props.valid:
                ret.append(act.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="s", out_signature="o")
    def GetActivityById(self, actid):
        if self._activities.has_key(actid):
            act = self._activities[actid]
            if act.props.valid:
                return act.object_path()
        raise NotFoundError("The activity was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, out_signature="ao")
    def GetBuddies(self):
        ret = []
        for buddy in self._buddies.values():
            if buddy.props.valid:
                ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="ay", out_signature="o")
    def GetBuddyByPublicKey(self, key):
        key = psutils.bytes_to_string(key)
        if self._buddies.has_key(key):
            buddy = self._buddies[key]
            if buddy.props.valid:
                return buddy.object_path()
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
        color = self._owner.props.color
        activity = Activity(self._bus_name, objid, self._server_plugin,
                        id=actid, type=atype, name=name, color=color, local=True)
        activity.connect("validity-changed", self._activity_validity_changed_cb)
        self._activities[actid] = activity

        activity.join()
        activity.send_properties()

        return activity

    def _activity_validity_changed_cb(self, activity, valid):
        if valid:
            self.ActivityAppeared(activity.object_path())
            print "New Activity: %s (%s)" % (activity.props.name, activity.props.id)
        else:
            self.ActivityDisappeared(activity.object_path())
            print "Activity disappeared: %s (%s)" % (activity.props.name, activity.props.id)

    def _activity_properties_changed(self, tp, act_id, props):
        activity = self._activities.get(act_id)
        if activity:
            activity.set_properties(props)


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
