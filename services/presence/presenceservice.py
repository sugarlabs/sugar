# Copyright (C) 2007, Red Hat, Inc.
# Copyright (C) 2007 Collabora Ltd. <http://www.collabora.co.uk/>
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
import dbus
import dbus.service
from dbus.gobject_service import ExportedGObject
from dbus.mainloop.glib import DBusGMainLoop
import logging

from telepathy.client import ManagerRegistry, Connection
from telepathy.interfaces import (CONN_MGR_INTERFACE, CONN_INTERFACE)
from telepathy.constants import (CONNECTION_STATUS_CONNECTING,
    CONNECTION_STATUS_CONNECTED,
    CONNECTION_STATUS_DISCONNECTED)

from server_plugin import ServerPlugin
from linklocal_plugin import LinkLocalPlugin
from sugar import util

from buddy import Buddy, ShellOwner
from activity import Activity
from psutils import pubkey_to_keyid

_PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
_PRESENCE_INTERFACE = "org.laptop.Sugar.Presence"
_PRESENCE_PATH = "/org/laptop/Sugar/Presence"


_logger = logging.getLogger('s-p-s.presenceservice')


class NotFoundError(dbus.DBusException):
    def __init__(self, msg):
        dbus.DBusException.__init__(self, msg)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'

class PresenceService(ExportedGObject):
    __gtype_name__ = "PresenceService"

    __gsignals__ = {
        'connection-status': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_BOOLEAN]))
    }

    def _create_owner(self):
        # Overridden by TestPresenceService
        return ShellOwner(self, self._session_bus)

    def __init__(self):
        self._next_object_id = 0
        self._connected = False

        self._buddies = {}              # identifier -> Buddy
        self._buddies_by_pubkey = {}    # base64 public key -> Buddy
        self._handles_buddies = {}      # tp client -> (handle -> Buddy)

        self._activities = {}           # activity id -> Activity

        self._session_bus = dbus.SessionBus()
        self._session_bus.add_signal_receiver(self._connection_disconnected_cb,
                signal_name="Disconnected",
                dbus_interface="org.freedesktop.DBus")

        # Create the Owner object
        self._owner = self._create_owner()
        key = self._owner.props.key
        keyid = pubkey_to_keyid(key)
        self._buddies['keyid/' + keyid] = self._owner
        self._buddies_by_pubkey[key] = self._owner

        self._registry = ManagerRegistry()
        self._registry.LoadManagers()

        # Set up the server connection
        self._server_plugin = ServerPlugin(self._registry, self._owner)
        self._handles_buddies[self._server_plugin] = {}

        self._server_plugin.connect('status', self._server_status_cb)
        self._server_plugin.connect('contact-online', self._contact_online)
        self._server_plugin.connect('contact-offline', self._contact_offline)
        self._server_plugin.connect('avatar-updated', self._avatar_updated)
        self._server_plugin.connect('buddy-properties-changed',
                                    self._buddy_properties_changed)
        self._server_plugin.connect('buddy-activities-changed',
                                    self._buddy_activities_changed)
        self._server_plugin.connect('activity-invitation',
                                    self._activity_invitation)
        self._server_plugin.connect('private-invitation',
                                    self._private_invitation)
        self._server_plugin.connect('activity-properties-changed',
                                    self._activity_properties_changed)
        self._server_plugin.start()

        # Set up the link local connection
        self._ll_plugin = LinkLocalPlugin(self._registry, self._owner)
        self._handles_buddies[self._ll_plugin] = {}

        ExportedGObject.__init__(self, self._session_bus, _PRESENCE_PATH)

        # for activation to work in a race-free way, we should really
        # export the bus name only after we export our initial object;
        # so this comes after the parent __init__
        self._bus_name = dbus.service.BusName(_PRESENCE_SERVICE,
                                              bus=self._session_bus)

    def _connection_disconnected_cb(self, foo=None):
        """Log event when D-Bus kicks us off the bus for some reason"""
        _logger.debug("Disconnected from session bus!!!")

    def _server_status_cb(self, plugin, status, reason):

        # FIXME: figure out connection status when we have a salut plugin too
        old_status = self._connected
        if status == CONNECTION_STATUS_CONNECTED:
            self._connected = True
            self._handles_buddies[plugin][plugin.self_handle] = self._owner
            self._owner.add_telepathy_handle(plugin, plugin.self_handle)
        else:
            self._connected = False
            if plugin.self_handle is not None:
                self._handles_buddies.setdefault(plugin, {}).pop(
                        plugin.self_handle, None)
                self._owner.remove_telepathy_handle(plugin, plugin.self_handle)

        if self._connected != old_status:
            self.emit('connection-status', self._connected)

    def get_buddy(self, objid):
        buddy = self._buddies.get(objid)
        if buddy is None:
            _logger.debug('Creating new buddy at .../%s', objid)
            # we don't know yet this buddy
            buddy = Buddy(self._session_bus, objid)
            buddy.connect("validity-changed", self._buddy_validity_changed_cb)
            buddy.connect("disappeared", self._buddy_disappeared_cb)
            self._buddies[objid] = buddy
        return buddy

    def _contact_online(self, tp, objid, handle, props):
        _logger.debug('Handle %u, .../%s is now online', handle, objid)
        buddy = self.get_buddy(objid)

        self._handles_buddies[tp][handle] = buddy
        # store the handle of the buddy for this CM
        buddy.add_telepathy_handle(tp, handle)
        buddy.set_properties(props)

    def _buddy_validity_changed_cb(self, buddy, valid):
        if valid:
            self.BuddyAppeared(buddy.object_path())
            self._buddies_by_pubkey[buddy.props.key] = buddy
            _logger.debug("New Buddy: %s (%s)", buddy.props.nick,
                          buddy.props.color)
        else:
            self.BuddyDisappeared(buddy.object_path())
            self._buddies_by_pubkey.pop(buddy.props.key, None)
            _logger.debug("Buddy left: %s (%s)", buddy.props.nick,
                          buddy.props.color)

    def _buddy_disappeared_cb(self, buddy):
        if buddy.props.valid:
            self.BuddyDisappeared(buddy.object_path())
            _logger.debug('Buddy left: %s (%s)', buddy.props.nick,
                          buddy.props.color)
            self._buddies_by_pubkey.pop(buddy.props.key, None)
        self._buddies.pop(buddy.props.objid, None)

    def _contact_offline(self, tp, handle):
        if not self._handles_buddies[tp].has_key(handle):
            return

        buddy = self._handles_buddies[tp].pop(handle)
        # the handle of the buddy for this CM is not valid anymore
        # (this might trigger _buddy_disappeared_cb if they are not visible
        # via any CM)
        buddy.remove_telepathy_handle(tp, handle)

    def _get_next_object_id(self):
        """Increment and return the object ID counter."""
        self._next_object_id = self._next_object_id + 1
        return self._next_object_id

    def _avatar_updated(self, tp, handle, avatar):
        buddy = self._handles_buddies[tp].get(handle)
        if buddy and not buddy.props.owner:
            _logger.debug("Buddy %s icon updated" % buddy.props.nick)
            buddy.props.icon = avatar

    def _buddy_properties_changed(self, tp, handle, properties):
        buddy = self._handles_buddies[tp].get(handle)
        if buddy:
            buddy.set_properties(properties)
            _logger.debug("Buddy %s properties updated: %s", buddy.props.nick,
                          properties.keys())

    def _new_activity(self, activity_id, tp):
        try:
            objid = self._get_next_object_id()
            activity = Activity(self._session_bus, objid, self, tp,
                                id=activity_id)
        except Exception:
            # FIXME: catching bare Exception considered harmful
            _logger.debug("Invalid activity:", exc_info=1)
            return None

        activity.connect("validity-changed",
                         self._activity_validity_changed_cb)
        activity.connect("disappeared", self._activity_disappeared_cb)
        self._activities[activity_id] = activity
        return activity

    def _activity_disappeared_cb(self, activity):
        _logger.debug("activity %s disappeared" % activity.props.id)

        self.ActivityDisappeared(activity.object_path())
        del self._activities[activity.props.id]

    def _buddy_activities_changed(self, tp, contact_handle, activities):
        acts = []
        for act in activities:
            acts.append(str(act))
        _logger.debug("Handle %s activities changed: %s", contact_handle, acts)
        buddies = self._handles_buddies[tp]
        buddy = buddies.get(contact_handle)

        if not buddy:
            # We don't know this buddy
            # FIXME: What should we do here?
            # FIXME: Do we need to check if the buddy is valid or something?
            _logger.debug("contact_activities_changed: buddy unknown")
            return

        old_activities = set()
        for activity in buddy.get_joined_activities():
            old_activities.add(activity.props.id)

        new_activities = set(activities)

        activities_joined = new_activities - old_activities
        for act in activities_joined:
            _logger.debug("Handle %s joined activity %s", contact_handle, act)
            activity = self._activities.get(act)
            if activity is None:
                # new activity, can fail
                activity = self._new_activity(act, tp)

            if activity is not None:
                activity.buddy_apparently_joined(buddy)

        activities_left = old_activities - new_activities
        for act in activities_left:
            _logger.debug("Handle %s left activity %s", contact_handle, act)
            activity = self._activities.get(act)
            if not activity:
                continue

            activity.buddy_apparently_left(buddy)

    def _activity_invitation(self, tp, act_id):
        activity = self._activities.get(act_id)
        if activity:
            self.ActivityInvitation(activity.object_path())

    def _private_invitation(self, tp, chan_path):
        conn = tp.get_connection()
        self.PrivateInvitation(str(conn.service_name), conn.object_path,
                               chan_path)

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

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature='',
                         out_signature="ao")
    def GetActivities(self):
        ret = []
        for act in self._activities.values():
            if act.props.valid:
                ret.append(act.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="s",
                         out_signature="o")
    def GetActivityById(self, actid):
        act = self._activities.get(actid, None)
        if not act or not act.props.valid:
            raise NotFoundError("The activity was not found.")
        return act.object_path()

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature='',
                         out_signature="ao")
    def GetBuddies(self):
        ret = []
        for buddy in self._buddies.values():
            if buddy.props.valid:
                ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE,
                         in_signature="ay", out_signature="o",
                         byte_arrays=True)
    def GetBuddyByPublicKey(self, key):
        buddy = self._buddies_by_pubkey.get(key)
        if buddy is not None:
            if buddy.props.valid:
                return buddy.object_path()
        raise NotFoundError("The buddy was not found.")

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature='sou',
                         out_signature='o')
    def GetBuddyByTelepathyHandle(self, tp_conn_name, tp_conn_path, handle):
        """Get the buddy corresponding to a Telepathy handle.

        :Parameters:
            `tp_conn_name` : str
                The well-known bus name of a Telepathy connection
            `tp_conn_path` : dbus.ObjectPath
                The object path of the Telepathy connection
            `handle` : int or long
                The handle of a Telepathy contact on that connection,
                of type HANDLE_TYPE_CONTACT. This may not be a
                channel-specific handle.
        :Returns: the object path of a Buddy
        :Raises NotFoundError: if the buddy is not found.
        """
        for tp, handles in self._handles_buddies.iteritems():
            conn = tp.get_connection()
            if conn is None:
                continue
            if (conn.service_name == tp_conn_name
                and conn.object_path == tp_conn_path):
                buddy = handles.get(handle)
                if buddy is not None and buddy.props.valid:
                        return buddy.object_path()
                # either the handle is invalid, or we don't have a Buddy
                # object for that buddy because we don't have all their
                # details yet
                raise NotFoundError("The buddy %u was not found on the "
                                    "connection to %s:%s"
                                    % (handle, tp_conn_name, tp_conn_path))
        raise NotFoundError("The buddy %u was not found: we have no "
                            "connection to %s:%s" % (handle, tp_conn_name,
                                                     tp_conn_path))

    def map_handles_to_buddies(self, tp, tp_chan, handles, create=True):
        """

        :Parameters:
            `tp` : Telepathy plugin
                The server or link-local plugin
            `tp_chan` : telepathy.client.Channel or None
                If not None, the channel in which these handles are
                channel-specific
            `handles` : iterable over int or long
                The handles to be mapped to Buddy objects
            `create` : bool
                If true (default), if a corresponding `Buddy` object is not
                found, create one.
        :Returns:
            A dict mapping handles from `handles` to `Buddy` objects.
            If `create` is true, the dict's keys will be exactly the
            items of `handles` in some order. If `create` is false,
            the dict will contain no entry for handles for which no
            `Buddy` is already available.
        :Raises LookupError: if `tp` is not a plugin attached to this PS.
        """
        handle_to_buddy = self._handles_buddies[tp]

        ret = {}
        missing = []
        for handle in handles:
            buddy = handle_to_buddy.get(handle)
            if buddy is None:
                missing.append(handle)
            else:
                ret[handle] = buddy

        if missing and create:
            handle_to_objid = tp.identify_contacts(tp_chan, missing)
            for handle, objid in handle_to_objid.iteritems():
                buddy = self.get_buddy(objid)
                ret[handle] = buddy
                if tp_chan is None:
                    handle_to_buddy[handle] = buddy
        return ret

    @dbus.service.method(_PRESENCE_INTERFACE,
                         in_signature='', out_signature="o")
    def GetOwner(self):
        if not self._owner:
            raise NotFoundError("The owner was not found.")
        else:
            return self._owner.object_path()

    @dbus.service.method(_PRESENCE_INTERFACE, in_signature="sssa{sv}",
            out_signature="o", async_callbacks=('async_cb', 'async_err_cb'))
    def ShareActivity(self, actid, atype, name, properties, async_cb,
                      async_err_cb):
        self._share_activity(actid, atype, name, properties,
                             (async_cb, async_err_cb))

    @dbus.service.method(_PRESENCE_INTERFACE,
                         in_signature='', out_signature="so")
    def GetPreferredConnection(self):
        conn = self._server_plugin.get_connection()
        return str(conn.service_name), conn.object_path

    def cleanup(self):
        for tp in self._handles_buddies:
            tp.cleanup()

    def _share_activity(self, actid, atype, name, properties, callbacks):
        objid = self._get_next_object_id()
        # FIXME check which tp client we should use to share the activity
        color = self._owner.props.color
        activity = Activity(self._session_bus, objid, self,
                            self._server_plugin, id=actid, type=atype,
                            name=name, color=color, local=True)
        activity.connect("validity-changed",
                         self._activity_validity_changed_cb)
        self._activities[actid] = activity
        activity._share(callbacks, self._owner)

        # local activities are valid at creation by definition, but we can't
        # connect to the activity's validity-changed signal until its already
        # issued the signal, which happens in the activity's constructor
        # for local activities.
        self._activity_validity_changed_cb(activity, activity.props.valid)

    def _activity_validity_changed_cb(self, activity, valid):
        if valid:
            self.ActivityAppeared(activity.object_path())
            _logger.debug("New Activity: %s (%s)", activity.props.name,
                          activity.props.id)
        else:
            self.ActivityDisappeared(activity.object_path())
            _logger.debug("Activity disappeared: %s (%s)", activity.props.name,
                          activity.props.id)

    def _activity_properties_changed(self, tp, act_id, props):
        activity = self._activities.get(act_id)
        if activity:
            activity.set_properties(props)


def main(test_num=0, randomize=False):
    loop = gobject.MainLoop()
    dbus_mainloop_wrapper = DBusGMainLoop(set_as_default=True)

    if test_num > 0:
        from pstest import TestPresenceService
        ps = TestPresenceService(test_num, randomize)
    else:
        ps = PresenceService()

    try:
        loop.run()
    except KeyboardInterrupt:
        ps.cleanup()
        _logger.debug('Ctrl+C pressed, exiting...')

if __name__ == "__main__":
    main()
