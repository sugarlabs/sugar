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
import dbus
from sugar import util
import gtk
from buddyiconcache import BuddyIconCache
import logging
import os
import hashlib
import psutils

from telepathy.client import ConnectionManager, ManagerRegistry, Connection, Channel
from telepathy.interfaces import (
    CONN_MGR_INTERFACE, CONN_INTERFACE, CHANNEL_TYPE_CONTACT_LIST, CHANNEL_INTERFACE_GROUP, CONN_INTERFACE_ALIASING,
    CONN_INTERFACE_AVATARS, CONN_INTERFACE_PRESENCE, CHANNEL_TYPE_TEXT, CHANNEL_TYPE_STREAMED_MEDIA)
from telepathy.constants import (
    CONNECTION_HANDLE_TYPE_NONE, CONNECTION_HANDLE_TYPE_CONTACT,
    CONNECTION_STATUS_CONNECTED, CONNECTION_STATUS_DISCONNECTED, CONNECTION_STATUS_CONNECTING,
    CONNECTION_HANDLE_TYPE_LIST, CONNECTION_HANDLE_TYPE_CONTACT, CONNECTION_HANDLE_TYPE_ROOM,
    CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED)

CONN_INTERFACE_BUDDY_INFO = 'org.laptop.Telepathy.BuddyInfo'
CONN_INTERFACE_ACTIVITY_PROPERTIES = 'org.laptop.Telepathy.ActivityProperties'

_PROTOCOL = "jabber"

class InvalidBuddyError(Exception):
    pass

def _buddy_icon_save_cb(buf, data):
    data[0] += buf
    return True

def _get_buddy_icon_at_size(icon, maxw, maxh, maxsize):
    loader = gtk.gdk.PixbufLoader()
    loader.write(icon)
    loader.close()
    unscaled_pixbuf = loader.get_pixbuf()
    del loader

    pixbuf = unscaled_pixbuf.scale_simple(maxw, maxh, gtk.gdk.INTERP_BILINEAR)
    del unscaled_pixbuf

    data = [""]
    quality = 90
    img_size = maxsize + 1
    while img_size > maxsize:
        del data
        data = [""]
        pixbuf.save_to_callback(_buddy_icon_save_cb, "jpeg", {"quality":"%d" % quality}, data)
        quality -= 10
        img_size = len(data[0])
    del pixbuf

    if img_size > maxsize:
        del data
        raise RuntimeError("could not size image less than %d bytes" % maxsize)

    return str(data[0])
        

class ServerPlugin(gobject.GObject):
    __gsignals__ = {
        'contact-online':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'contact-offline': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT])),
        'status':          (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_INT, gobject.TYPE_INT])),
        'avatar-updated':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'buddy-properties-changed':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'buddy-activities-changed':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'activity-invitation': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT])),
        'private-invitation':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT])),
        'activity-properties-changed':  (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                             ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'activity-shared':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                                 gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'activity-joined':   (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT,
                                 gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }
    
    def __init__(self, registry, owner):
        gobject.GObject.__init__(self)

        self._icon_cache = BuddyIconCache()

        self._gabble_mgr = registry.GetManager('gabble')
        self._online_contacts = {}  # handle -> jid

        self._activities = {} # activity id -> handle
        self._joined_activities = [] # (activity_id, handle of the activity channel)

        self._owner = owner
        self._owner.connect("property-changed", self._owner_property_changed_cb)
        self._owner.connect("icon-changed", self._owner_icon_changed_cb)

        self._account = self._get_account_info()

        self._conn = self._init_connection()

        self._reconnect_id = 0

    def _owner_property_changed_cb(self, owner, properties):
        logging.debug("Owner properties changed: %s" % properties)

        if properties.has_key("current-activity"):
            self._set_self_current_activity()

        if properties.has_key("nick"):
            self._set_self_alias()

        if properties.has_key("color"):
            self._set_self_olpc_properties()

    def _owner_icon_changed_cb(self, owner, icon):
        logging.debug("Owner icon changed to size %d" % len(str(icon)))
        self._set_self_avatar(icon)

    def _get_account_info(self):
        account_info = {}
                        
        account_info['server'] = self._owner.get_server()

        khash = util.printable_hash(util._sha_data(self._owner.props.key))
        account_info['account'] = "%s@%s" % (khash, account_info['server'])

        account_info['password'] = self._owner.get_key_hash()
        account_info['register'] = not self._owner.get_registered()

        print "ACCT: %s" % account_info
        return account_info

    def _find_existing_connection(self):
        our_name = self._account['account']

        # Search existing connections, if any, that we might be able to use
        connections = Connection.get_connections()
        conn = None
        for item in connections:
            if not item.object_path.startswith("/org/freedesktop/Telepathy/Connection/gabble/jabber/"):
                continue
            if item[CONN_INTERFACE].GetProtocol() != _PROTOCOL:
                continue
            if item[CONN_INTERFACE].GetStatus() == CONNECTION_STATUS_CONNECTED:
                test_handle = item[CONN_INTERFACE].RequestHandles(CONNECTION_HANDLE_TYPE_CONTACT, [our_name])[0]
                if item[CONN_INTERFACE].GetSelfHandle() != test_handle:
                    continue
            return item
        return None

    def get_connection(self):
        return self._conn

    def _init_connection(self):
        conn = self._find_existing_connection()
        if not conn:
            acct = self._account.copy()

            # Create a new connection
            name, path = self._gabble_mgr[CONN_MGR_INTERFACE].RequestConnection(_PROTOCOL, acct)
            conn = Connection(name, path)
            del acct

        conn[CONN_INTERFACE].connect_to_signal('StatusChanged', self._status_changed_cb)
        conn[CONN_INTERFACE].connect_to_signal('NewChannel', self._new_channel_cb)

        # hack
        conn._valid_interfaces.add(CONN_INTERFACE_PRESENCE)
        conn._valid_interfaces.add(CONN_INTERFACE_BUDDY_INFO)
        conn._valid_interfaces.add(CONN_INTERFACE_ACTIVITY_PROPERTIES)
        conn._valid_interfaces.add(CONN_INTERFACE_AVATARS)
        conn._valid_interfaces.add(CONN_INTERFACE_ALIASING)

        conn[CONN_INTERFACE_PRESENCE].connect_to_signal('PresenceUpdate',
            self._presence_update_cb)

        return conn

    def _request_list_channel(self, name):
        handle = self._conn[CONN_INTERFACE].RequestHandles(
            CONNECTION_HANDLE_TYPE_LIST, [name])[0]
        chan_path = self._conn[CONN_INTERFACE].RequestChannel(
            CHANNEL_TYPE_CONTACT_LIST, CONNECTION_HANDLE_TYPE_LIST,
            handle, True)
        channel = Channel(self._conn._dbus_object._named_service, chan_path)
        # hack
        channel._valid_interfaces.add(CHANNEL_INTERFACE_GROUP)
        return channel

    def _connected_cb(self):
        if self._account['register']:
            # we successfully register this account
            self._owner.props.registered = True

        # the group of contacts who may receive your presence
        publish = self._request_list_channel('publish')
        publish_handles, local_pending, remote_pending = publish[CHANNEL_INTERFACE_GROUP].GetAllMembers()

        # the group of contacts for whom you wish to receive presence
        subscribe = self._request_list_channel('subscribe')
        subscribe_handles = subscribe[CHANNEL_INTERFACE_GROUP].GetMembers()

        if local_pending:
            # accept pending subscriptions
            #print 'pending: %r' % local_pending
            publish[CHANNEL_INTERFACE_GROUP].AddMembers(local_pending, '')

        not_subscribed = list(set(publish_handles) - set(subscribe_handles))
        self_handle = self._conn[CONN_INTERFACE].GetSelfHandle()
        self._online_contacts[self_handle] = self._account['account']

        for handle in not_subscribed:
            # request subscriptions from people subscribed to us if we're not subscribed to them
            subscribe[CHANNEL_INTERFACE_GROUP].AddMembers([self_handle], '')

        if CONN_INTERFACE_BUDDY_INFO not in self._conn.get_valid_interfaces():
            logging.debug('OLPC information not available')
            self.cleanup()
            return

        self._conn[CONN_INTERFACE_BUDDY_INFO].connect_to_signal('PropertiesChanged',
                self._buddy_properties_changed_cb)
        self._conn[CONN_INTERFACE_BUDDY_INFO].connect_to_signal('ActivitiesChanged',
                self._buddy_activities_changed_cb)
        self._conn[CONN_INTERFACE_BUDDY_INFO].connect_to_signal('CurrentActivityChanged',
                self._buddy_current_activity_changed_cb)

        self._conn[CONN_INTERFACE_AVATARS].connect_to_signal('AvatarUpdated',
                self._avatar_updated_cb)
        self._conn[CONN_INTERFACE_ALIASING].connect_to_signal('AliasesChanged',
                self._alias_changed_cb)
        self._conn[CONN_INTERFACE_ACTIVITY_PROPERTIES].connect_to_signal('ActivityPropertiesChanged',
                self._activity_properties_changed_cb)

        # Set initial buddy properties, avatar, and activities
        self._set_self_olpc_properties(True)
        self._set_self_alias()
        self._set_self_activities()
        self._set_self_current_activity()
        self._set_self_avatar()

        # Request presence for everyone on the channel
        self._conn[CONN_INTERFACE_PRESENCE].GetPresence(subscribe_handles,
                ignore_reply=True)

    def _set_self_avatar_cb(self, token):
        self._icon_cache.set_avatar(hash, token)

    def _set_self_avatar(self, icon_data=None):
        if not icon_data:
            icon_data = self._owner.props.icon

        md5 = hashlib.md5()
        md5.update(icon_data)
        hash = md5.hexdigest()

        self_handle = self._conn[CONN_INTERFACE].GetSelfHandle()
        token = self._conn[CONN_INTERFACE_AVATARS].GetAvatarTokens([self_handle])[0]

        if self._icon_cache.check_avatar(hash, token):
            # avatar is up to date
            return

        types, minw, minh, maxw, maxh, maxsize = self._conn[CONN_INTERFACE_AVATARS].GetAvatarRequirements()
        if not "image/jpeg" in types:
            logging.debug("server does not accept JPEG format avatars.")
            return

        img_data = _get_buddy_icon_at_size(icon_data, min(maxw, 96), min(maxh, 96), maxsize)
        self._conn[CONN_INTERFACE_AVATARS].SetAvatar(img_data, "image/jpeg",
                reply_handler=self._set_self_avatar_cb,
                error_handler=lambda *args: self._log_error_cb("setting avatar", *args))

    def _join_activity_create_channel_cb(self, activity_id, signal, handle, userdata, chan_path):
        channel = Channel(self._conn._dbus_object._named_service, chan_path)
        self._joined_activities.append((activity_id, handle))
        self._set_self_activities()
        self.emit(signal, activity_id, channel, None, userdata)

    def _join_activity_get_channel_cb(self, activity_id, signal, userdata, handles):
        if not self._activities.has_key(activity_id):
            self._activities[activity_id] = handles[0]

        if (activity_id, handles[0]) in self._joined_activities:
            e = RuntimeError("Already joined activity %s" % activity_id)
            logging.debug(str(e))
            self.emit(signal, activity_id, None, e, userdata)
            return

        self._conn[CONN_INTERFACE].RequestChannel(CHANNEL_TYPE_TEXT,
            CONNECTION_HANDLE_TYPE_ROOM, handles[0], True,
            reply_handler=lambda *args: self._join_activity_create_channel_cb(activity_id, signal, handles[0], userdata, *args),
            error_handler=lambda *args: self._join_error_cb(activity_id, signal, userdata, *args))

    def _join_error_cb(self, activity_id, signal, userdata, err):
        e = Exception("Error joining/sharing activity %s: %s" % (activity_id, err))
        logging.debug(str(e))
        self.emit(signal, activity_id, None, e, userdata)

    def _internal_join_activity(self, activity_id, signal, userdata):
        handle = self._activities.get(activity_id)
        if not handle:
            self._conn[CONN_INTERFACE].RequestHandles(CONNECTION_HANDLE_TYPE_ROOM, [activity_id],
                    reply_handler=lambda *args: self._join_activity_get_channel_cb(activity_id, signal, userdata, *args),
                    error_handler=lambda *args: self._join_error_cb(activity_id, signal, userdata, *args))
        else:
            self._join_activity_get_channel_cb(activity_id, userdata, [handle])
    
    def share_activity(self, activity_id, userdata):
        self._internal_join_activity(activity_id, "activity-shared", userdata)

    def join_activity(self, activity_id, userdata):
        self._internal_join_activity(activity_id, "activity-joined", userdata)

    def _ignore_success_cb(self):
        pass

    def _log_error_cb(self, msg, err):
        logging.debug("Error %s: %s" % (msg, err))

    def _set_self_olpc_properties(self, set_key=False):
        props = {}
        props['color'] = self._owner.props.color
        if set_key:
            props['key'] = dbus.ByteArray(self._owner.props.key)
        self._conn[CONN_INTERFACE_BUDDY_INFO].SetProperties(props,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting properties", *args))

    def _set_self_alias(self):
        alias = self._owner.props.nick
        self_handle = self._conn[CONN_INTERFACE].GetSelfHandle()
        self._conn[CONN_INTERFACE_ALIASING].SetAliases({self_handle : alias},
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting alias", *args))

    def _set_self_activities(self):
        self._conn[CONN_INTERFACE_BUDDY_INFO].SetActivities(self._joined_activities,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting activities", *args))

    def _set_self_current_activity(self):
        cur_activity = self._owner.props.current_activity
        cur_activity_handle = 0
        if not cur_activity:
            cur_activity = ""
        else:
            cur_activity_handle = self._get_handle_for_activity(cur_activity)
            if not cur_activity_handle:
                # dont advertise a current activity that's not shared
                cur_activity = ""

        logging.debug("Setting current activity to '%s' (handle %s)" % (cur_activity, cur_activity_handle))
        self._conn[CONN_INTERFACE_BUDDY_INFO].SetCurrentActivity(cur_activity,
                cur_activity_handle,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting current activity", *args))

    def _get_handle_for_activity(self, activity_id):
        for (act, handle) in self._joined_activities:
            if activity_id == act:
                return handle
        return None

    def _status_changed_cb(self, state, reason):
        if state == CONNECTION_STATUS_CONNECTING:
            logging.debug("State: connecting...")
        elif state == CONNECTION_STATUS_CONNECTED:
            logging.debug("State: connected")
            self._connected_cb()
            self.emit('status', state, int(reason))
        elif state == CONNECTION_STATUS_DISCONNECTED:
            logging.debug("State: disconnected (reason %r)" % reason)
            self.emit('status', state, int(reason))
            self._conn = None
            if reason == CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED:
                # FIXME: handle connection failure; retry later?
                pass
        return False

    def start(self):
        logging.debug("Starting up...")
        # If the connection is already connected query initial contacts
        conn_status = self._conn[CONN_INTERFACE].GetStatus()
        if conn_status == CONNECTION_STATUS_CONNECTED:
            self._connected_cb()
            subscribe = self._request_list_channel('subscribe')
            subscribe_handles = subscribe[CHANNEL_INTERFACE_GROUP].GetMembers()
            self._conn[CONN_INTERFACE_PRESENCE].RequestPresence(subscribe_handles)
        elif conn_status == CONNECTION_STATUS_CONNECTING:
            pass
        else:
            self._conn[CONN_INTERFACE].Connect(reply_handler=self._connect_reply_cb,
                    error_handler=self._connect_error_cb)

    def _connect_reply_cb(self):
        if self._reconnect_id > 0:
            gobject.source_remove(self._reconnect_id)

    def _reconnect(self):
        self._reconnect_id = 0
        self.start()
        return False

    def _connect_error_cb(self, exception):
        logging.debug("Connect error: %s" % exception)
        if not self._reconnect_id:
            self._reconnect_id = gobject.timeout_add(10000, self._reconnect)

    def cleanup(self):
        if not self._conn:
            return
        self._conn[CONN_INTERFACE].Disconnect()

    def _contact_offline(self, handle):
        if not self._online_contacts.has_key(handle):
            return
        if self._online_contacts[handle]:
            self.emit("contact-offline", handle)
        del self._online_contacts[handle]

    def _contact_online_activities_cb(self, handle, activities):
        self._buddy_activities_changed_cb(handle, activities)

    def _contact_online_activities_error_cb(self, handle, err):
        logging.debug("Handle %s - Error getting activities: %s" % (handle, err))
        self._contact_offline(handle)

    def _contact_online_aliases_cb(self, handle, props, aliases):
        if not aliases or not len(aliases):
            logging.debug("Handle %s - No aliases" % handle)
            self._contact_offline(handle)
            return

        props['nick'] = aliases[0]
        jid = self._conn[CONN_INTERFACE].InspectHandles(CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0]
        self._online_contacts[handle] = jid
        self.emit("contact-online", handle, props)

        self._conn[CONN_INTERFACE_BUDDY_INFO].GetActivities(handle,
            reply_handler=lambda *args: self._contact_online_activities_cb(handle, *args),
            error_handler=lambda *args: self._contact_online_activities_error_cb(handle, *args))

    def _contact_online_aliases_error_cb(self, handle, err):
        logging.debug("Handle %s - Error getting nickname: %s" % (handle, err))
        self._contact_offline(handle)

    def _contact_online_properties_cb(self, handle, props):
        if not props.has_key('key'):
            logging.debug("Handle %s - invalid key." % handle)
            self._contact_offline(handle)
            return
        if not props.has_key('color'):
            logging.debug("Handle %s - invalid color." % handle)
            self._contact_offline(handle)
            return

        # Convert key from dbus byte array to python string
        props["key"] = psutils.bytes_to_string(props["key"])

        self._conn[CONN_INTERFACE_ALIASING].RequestAliases([handle],
            reply_handler=lambda *args: self._contact_online_aliases_cb(handle, props, *args),
            error_handler=lambda *args: self._contact_online_aliases_error_cb(handle, *args))
        
    def _contact_online_properties_error_cb(self, handle, err):
        logging.debug("Handle %s - Error getting properties: %s" % (handle, err))
        self._contact_offline(handle)

    def _contact_online(self, handle):
        self._online_contacts[handle] = None
        self._conn[CONN_INTERFACE_BUDDY_INFO].GetProperties(handle,
            reply_handler=lambda *args: self._contact_online_properties_cb(handle, *args),
            error_handler=lambda *args: self._contact_online_properties_error_cb(handle, *args))

    def _presence_update_cb(self, presence):
        for handle in presence:
            timestamp, statuses = presence[handle]
            online = handle in self._online_contacts
            for status, params in statuses.items():
                jid = self._conn[CONN_INTERFACE].InspectHandles(CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0]
                olstr = "ONLINE"
                if not online: olstr = "OFFLINE"
                logging.debug("Handle %s (%s) was %s, status now '%s'." % (handle, jid, olstr, status))
                if not online and status in ["available", "away", "brb", "busy", "dnd", "xa"]:
                    self._contact_online(handle)
                elif status in ["offline", "invisible"]:
                    self._contact_offline(handle)

    def _avatar_updated_cb(self, handle, new_avatar_token):
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            # ignore network events for Owner property changes since those
            # are handled locally
            return

        if not self._online_contacts.has_key(handle):
            logging.debug("Handle %s not valid yet...")
            return

        jid = self._online_contacts[handle]
        if not jid:
            logging.debug("Handle %s not valid yet...")
            return

        icon = self._icon_cache.get_icon(jid, new_avatar_token)
        if not icon:
            # cache miss
            avatar, mime_type = self._conn[CONN_INTERFACE_AVATARS].RequestAvatar(handle)
            icon = ''.join(map(chr, avatar))
            self._icon_cache.store_icon(jid, new_avatar_token, icon)

        self.emit("avatar-updated", handle, icon)

    def _alias_changed_cb(self, aliases):
        for handle, alias in aliases:
            prop = {'nick': alias}
            #print "Buddy %s alias changed to %s" % (handle, alias)
            if self._online_contacts.has_key(handle) and self._online_contacts[handle]:
                self._buddy_properties_changed_cb(handle, prop)

    def _buddy_properties_changed_cb(self, handle, properties):
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            # ignore network events for Owner property changes since those
            # are handled locally
            return
        if self._online_contacts.has_key(handle) and self._online_contacts[handle]:
	        self.emit("buddy-properties-changed", handle, properties)

    def _buddy_activities_changed_cb(self, handle, activities):
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            # ignore network events for Owner activity changes since those
            # are handled locally
            return
        if not self._online_contacts.has_key(handle) or not self._online_contacts[handle]:
            return

        for act_id, act_handle in activities:
            self._activities[act_id] = act_handle
        activities_id = map(lambda x: x[0], activities)
        self.emit("buddy-activities-changed", handle, activities_id)

    def _buddy_current_activity_changed_cb(self, handle, activity, channel):
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            # ignore network events for Owner current activity changes since those
            # are handled locally
            return
        if not self._online_contacts.has_key(handle) or not self._online_contacts[handle]:
            return

        if not len(activity) or not util.validate_activity_id(activity):
            activity = None
        prop = {'current-activity': activity}
        logging.debug("Handle %s: current activity now %s" % (handle, activity))
        self._buddy_properties_changed_cb(handle, prop)

    def _new_channel_cb(self, object_path, channel_type, handle_type, handle, suppress_handler):
        if handle_type == CONNECTION_HANDLE_TYPE_ROOM and channel_type == CHANNEL_TYPE_TEXT:
            channel = Channel(self._conn._dbus_object._named_service, object_path)

            # hack
            channel._valid_interfaces.add(CHANNEL_INTERFACE_GROUP)

            current, local_pending, remote_pending = channel[CHANNEL_INTERFACE_GROUP].GetAllMembers()
            
            if local_pending:
                for act_id, act_handle in self._activities.items():
                    if handle == act_handle:
                        self.emit("activity-invitation", act_id)

        elif handle_type == CONNECTION_HANDLE_TYPE_CONTACT and \
            channel_type in [CHANNEL_TYPE_TEXT, CHANNEL_TYPE_STREAMED_MEDIA]:
            self.emit("private-invitation", object_path)

    def update_activity_properties(self, act_id):
        handle = self._activities.get(act_id)
        if not handle:
            raise RuntimeError("Unknown activity %s: couldn't find handle.")

        self._conn[CONN_INTERFACE_ACTIVITY_PROPERTIES].GetProperties(handle,
                reply_handler=lambda *args: self._activity_properties_changed_cb(handle, *args),
                error_handler=lambda *args: self._log_error_cb("getting activity properties", *args))

    def set_activity_properties(self, act_id, props):
        handle = self._activities.get(act_id)
        if not handle:
            raise RuntimeError("Unknown activity %s: couldn't find handle.")

        self._conn[CONN_INTERFACE_ACTIVITY_PROPERTIES].SetProperties(handle, props,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting activity properties", *args))

    def _activity_properties_changed_cb(self, room, properties):
        for act_id, act_handle in self._activities.items():
            if room == act_handle:
                self.emit("activity-properties-changed", act_id, properties)
                return
