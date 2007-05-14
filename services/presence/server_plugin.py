"""Telepathy-python presence server interface/implementation plugin"""
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

import sys
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
    """(Unused) exception to indicate an invalid buddy specifier"""

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
    """Telepathy-python-based presence server interface
    
    The ServerPlugin instance translates network events from 
    Telepathy Python into GObject events.  It provides direct 
    python calls to perform the required network operations 
    to implement the PresenceService.
    """
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
        """Initialize the ServerPlugin instance 
        
        registry -- telepathy.client.ManagerRegistry from the 
            PresenceService, used to find the "gabble" connection 
            manager in this case...
        owner -- presence.buddy.GenericOwner instance (normally a 
            presence.buddy.ShellOwner instance)
        """
        gobject.GObject.__init__(self)

        self._icon_cache = BuddyIconCache()

        self._registry = registry
        self._online_contacts = {}  # handle -> jid

        self._activities = {} # activity id -> handle
        self._joined_activities = [] # (activity_id, handle of the activity channel)

        self._owner = owner
        self._owner.connect("property-changed", self._owner_property_changed_cb)
        self._owner.connect("icon-changed", self._owner_icon_changed_cb)

        self._account = self._get_account_info()
        self._conn_status = CONNECTION_STATUS_DISCONNECTED
        self._reconnect_id = 0

        # Monitor IPv4 address as an indicator of the network connection
        self._ip4am = psutils.IP4AddressMonitor.get_instance()
        self._ip4am.connect('address-changed', self._ip4_address_changed_cb)

    def _ip4_address_changed_cb(self, ip4am, address):
        logging.debug("::: IP4 address now %s" % address)
        if address:
            logging.debug("::: valid IP4 address, conn_status %s" % self._conn_status)
            if self._conn_status == CONNECTION_STATUS_DISCONNECTED:
                logging.debug("::: will connect")
                self.start()
        else:
            logging.debug("::: invalid IP4 address, will disconnect")
            self.cleanup()

    def _owner_property_changed_cb(self, owner, properties):
        """Local user's configuration properties have changed 
        
        owner -- the Buddy object for the local user 
        properties -- set of updated properties 
        
        calls:
        
            _set_self_current_activity    current-activity
            _set_self_alias    nick
            _set_self_olpc_properties   color
        
        depending on which properties are present in the 
        set of properties.
        """
        logging.debug("Owner properties changed: %s" % properties)

        if properties.has_key("current-activity"):
            self._set_self_current_activity()

        if properties.has_key("nick"):
            self._set_self_alias()

        if properties.has_key("color") or properties.has_key("ip4-address"):
            if self._conn_status == CONNECTION_STATUS_CONNECTED:
                self._set_self_olpc_properties()

    def _owner_icon_changed_cb(self, owner, icon):
        """Owner has changed their icon, forward to network"""
        logging.debug("Owner icon changed to size %d" % len(str(icon)))
        self._set_self_avatar(icon)

    def _get_account_info(self):
        """Retrieve metadata dictionary describing this account 
        
        returns dictionary with:
        
            server : server url from owner 
            account : printable-ssh-key-hash@server
            password : ssh-key-hash
            register : whether to register (i.e. whether not yet 
                registered)
        """
        account_info = {}
                        
        account_info['server'] = self._owner.get_server()

        khash = util.printable_hash(util._sha_data(self._owner.props.key))
        account_info['account'] = "%s@%s" % (khash, account_info['server'])

        account_info['password'] = self._owner.get_key_hash()
        account_info['register'] = not self._owner.get_registered()

        print "ACCT: %s" % account_info
        return account_info

    def _find_existing_connection(self):
        """Try to find an existing Telepathy connection to this server 
        
        filters the set of connections from 
            telepathy.client.Connection.get_connections
        to find a connection using our protocol with the 
        "self handle" of that connection being a handle 
        which matches our account (see _get_account_info)
        
        returns connection or None
        """
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
        """Retrieve our telepathy.client.Connection object"""
        return self._conn

    def _connect_reply_cb(self):
        """Handle connection success"""
        pass

    def _connect_error_cb(self, exception):
        """Handle connection failure"""
        logging.debug("Connect error: %s" % exception)

    def _init_connection(self):
        """Set up our connection 
        
        if there is no existing connection 
            (_find_existing_connection returns None)
        produce a new connection with our protocol for our
        account.
        
        if there is an existing connection, reuse it by 
        registering for various of events on it.
        """
        conn = self._find_existing_connection()
        if not conn:
            acct = self._account.copy()

            # Create a new connection
            gabble_mgr = self._registry.GetManager('gabble')
            name, path = gabble_mgr[CONN_MGR_INTERFACE].RequestConnection(_PROTOCOL, acct)
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

        self._conn = conn
        status = self._conn[CONN_INTERFACE].GetStatus()
        if status == CONNECTION_STATUS_DISCONNECTED:
            self._conn[CONN_INTERFACE].Connect(reply_handler=self._connect_reply_cb,
                    error_handler=self._connect_error_cb)
        self._handle_connection_status_change(self._conn, status)

    def _request_list_channel(self, name):
        """Request a contact-list channel from Telepathy
        
        name -- publish/subscribe, for the type of channel
        """
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
        """Callback on successful connection to a server 
        """

        if self._account['register']:
            # we successfully register this account
            self._owner.set_registered(True)

        # the group of contacts who may receive your presence
        publish = self._request_list_channel('publish')
        publish_handles, local_pending, remote_pending = publish[CHANNEL_INTERFACE_GROUP].GetAllMembers()

        # the group of contacts for whom you wish to receive presence
        subscribe = self._request_list_channel('subscribe')
        subscribe_handles = subscribe[CHANNEL_INTERFACE_GROUP].GetMembers()

        if local_pending:
            # accept pending subscriptions
            publish[CHANNEL_INTERFACE_GROUP].AddMembers(local_pending, '')

        self_handle = self._conn[CONN_INTERFACE].GetSelfHandle()
        self._online_contacts[self_handle] = self._account['account']

        # request subscriptions from people subscribed to us if we're not subscribed to them
        not_subscribed = list(set(publish_handles) - set(subscribe_handles))
        subscribe[CHANNEL_INTERFACE_GROUP].AddMembers(not_subscribed, '')

        if CONN_INTERFACE_BUDDY_INFO not in self._conn.get_valid_interfaces():
            logging.debug('OLPC information not available')
            return False

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
        self._set_self_olpc_properties()
        self._set_self_alias()
        self._set_self_activities()
        self._set_self_current_activity()
        self._set_self_avatar()

        # Request presence for everyone on the channel
        subscribe_handles = subscribe[CHANNEL_INTERFACE_GROUP].GetMembers()
        self._conn[CONN_INTERFACE_PRESENCE].RequestPresence(subscribe_handles)
        return True

    def _set_self_avatar_cb(self, token):
        self._icon_cache.set_avatar(hash, token)

    def _set_self_avatar(self, icon_data=None):
        if not icon_data:
            icon_data = self._owner.props.icon

        m = None
        if sys.version_info[:3] >= (2, 5, 0):
            import hashlib
            m = hashlib.md5()
        else:
            import md5
            m = md5.new()

        m.update(icon_data)
        hash = m.hexdigest()

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
            # FIXME: figure out why the server can't figure this out itself
            room_jid = activity_id + "@conference." + self._account["server"]
            self._conn[CONN_INTERFACE].RequestHandles(CONNECTION_HANDLE_TYPE_ROOM, [room_jid],
                    reply_handler=lambda *args: self._join_activity_get_channel_cb(activity_id, signal, userdata, *args),
                    error_handler=lambda *args: self._join_error_cb(activity_id, signal, userdata, *args))
        else:
            self._join_activity_get_channel_cb(activity_id, signal, userdata, [handle])
    
    def share_activity(self, activity_id, userdata):
        """Share activity with the network
        
        activity_id -- unique ID for the activity 
        userdata -- opaque token to be passed in the resulting event
            (id, callback, errback) normally
        
        Asks the Telepathy server to create a "conference" channel 
        for the activity or return a handle to an already created 
        conference channel for the activity.
        """
        self._internal_join_activity(activity_id, "activity-shared", userdata)

    def join_activity(self, activity_id, userdata):
        """Join an activity on the network (or locally)
        
        activity_id -- unique ID for the activity 
        userdata -- opaque token to be passed in the resulting event
            (id, callback, errback) normally
        
        Asks the Telepathy server to create a "conference" channel 
        for the activity or return a handle to an already created 
        conference channel for the activity.
        """
        self._internal_join_activity(activity_id, "activity-joined", userdata)

    def _ignore_success_cb(self):
        """Ignore an event (null-operation)"""

    def _log_error_cb(self, msg, err):
        """Log a message (error) at debug level with prefix msg"""
        logging.debug("Error %s: %s" % (msg, err))

    def _set_self_olpc_properties(self):
        """Set color and key on our Telepathy server identity"""
        props = {}
        props['color'] = self._owner.props.color
        props['key'] = dbus.ByteArray(self._owner.props.key)
        addr = self._owner.props.ip4_address
        if not addr:
            props['ip4-address'] = ""
        else:
            props['ip4-address'] = addr
        self._conn[CONN_INTERFACE_BUDDY_INFO].SetProperties(props,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting properties", *args))

    def _set_self_alias(self):
        """Forwarded to SetActivities on AliasInfo channel"""
        alias = self._owner.props.nick
        self_handle = self._conn[CONN_INTERFACE].GetSelfHandle()
        self._conn[CONN_INTERFACE_ALIASING].SetAliases({self_handle : alias},
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting alias", *args))

    def _set_self_activities(self):
        """Forward set of joined activities to network 
       
        uses SetActivities on BuddyInfo channel
        """
        self._conn[CONN_INTERFACE_BUDDY_INFO].SetActivities(self._joined_activities,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting activities", *args))

    def _set_self_current_activity(self):
        """Forward our current activity (or "") to network
       
        uses SetCurrentActivity on BuddyInfo channel
        """
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
        """Retrieve current handle for given activity or None"""
        for (act, handle) in self._joined_activities:
            if activity_id == act:
                return handle
        return None

    def _start_helper(self):
        """Helper so start() doesn't have to return False"""
        self.start()
        return False

    def _reconnect_cb(self):
        """Schedule a reconnection attempt"""
        gobject.idle_add(self._start_helper)
        self._reconnect_id = 0
        return False

    def _handle_connection_status_change(self, status, reason):
        if status == self._conn_status:
            return

        if status == CONNECTION_STATUS_CONNECTING:
            self._conn_status = status
            logging.debug("status: connecting...")
        elif status == CONNECTION_STATUS_CONNECTED:
            if self._connected_cb():
                logging.debug("status: connected")
                self._conn_status = status
            else:
                self.cleanup()
                logging.debug("status: was connected, but an error occurred")
        elif status == CONNECTION_STATUS_DISCONNECTED:
            self.cleanup()
            logging.debug("status: disconnected (reason %r)" % reason)
            if reason == CONNECTION_STATUS_REASON_AUTHENTICATION_FAILED:
                # FIXME: handle connection failure; retry later?
                pass
            else:
                # If disconnected, but still have a network connection, retry
                # If disconnected and no network connection, do nothing here
                # and let the IP4AddressMonitor address-changed signal handle
                # reconnection
                if self._ip4am.props.address:
                    self._reconnect_id = gobject.timeout_add(5000, self._reconnect_cb)

        self.emit('status', self._conn_status, int(reason))
        return False

    def _status_changed_cb(self, status, reason):
        """Handle notification of connection-status change
        
        status -- CONNECTION_STATUS_*
        reason -- integer code describing the reason...
        """
        logging.debug("::: connection status changed to %s" % status)
        self._handle_connection_status_change(status, reason)

    def start(self):
        """Start up the Telepathy networking connections
        
        if we are already connected, query for the initial contact
        information.
       
        if we are already connecting, do nothing
        
        otherwise initiate a connection and transfer control to 
            _connect_reply_cb or _connect_error_cb
        """
        logging.debug("Starting up...")

        if self._reconnect_id > 0:
            gobject.source_remove(self._reconnect_id)
            self._reconnect_id = 0

        # Only init connection if we have a valid IP address
        if self._ip4am.props.address:
            logging.debug("::: Have IP4 address %s, will connect" % self._ip4am.props.address)
            self._init_connection()
        else:
            logging.debug("::: No IP4 address, postponing connection")

    def cleanup(self):
        """If we still have a connection, disconnect it"""
        if self._conn:
            self._conn[CONN_INTERFACE].Disconnect()
        self._conn = None
        self._conn_status = CONNECTION_STATUS_DISCONNECTED

        for handle in self._online_contacts.keys():
            self._contact_offline(handle)
        self._online_contacts = {}
        self._joined_activites = []
        self._activites = {}

        if self._reconnect_id > 0:
            gobject.source_remove(self._reconnect_id)
            self._reconnect_id = 0

    def _contact_offline(self, handle):
        """Handle contact going offline (send message, update set)"""
        if not self._online_contacts.has_key(handle):
            return
        if self._online_contacts[handle]:
            self.emit("contact-offline", handle)
        del self._online_contacts[handle]

    def _contact_online_activities_cb(self, handle, activities):
        """Handle contact's activity list update"""
        self._buddy_activities_changed_cb(handle, activities)

    def _contact_online_activities_error_cb(self, handle, err):
        """Handle contact's activity list being unavailable"""
        logging.debug("Handle %s - Error getting activities: %s" % (handle, err))
        # Don't drop the buddy if we can't get their activities, for now
        #self._contact_offline(handle)

    def _contact_online_aliases_cb(self, handle, props, aliases):
        """Handle contact's alias being received (do further queries)"""
        if not self._conn or not aliases or not len(aliases):
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
        """Handle failure to retrieve given user's alias/information"""
        logging.debug("Handle %s - Error getting nickname: %s" % (handle, err))
        self._contact_offline(handle)

    def _contact_online_properties_cb(self, handle, props):
        """Handle failure to retrieve given user's alias/information"""
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
        """Handle error retrieving property-set for a user (handle)"""
        logging.debug("Handle %s - Error getting properties: %s" % (handle, err))
        self._contact_offline(handle)

    def _contact_online(self, handle):
        """Handle a contact coming online"""
        self._online_contacts[handle] = None
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            jid = self._conn[CONN_INTERFACE].InspectHandles(CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0]
            self._online_contacts[handle] = jid
            # ignore network events for Owner property changes since those
            # are handled locally
            return

        self._conn[CONN_INTERFACE_BUDDY_INFO].GetProperties(handle,
            reply_handler=lambda *args: self._contact_online_properties_cb(handle, *args),
            error_handler=lambda *args: self._contact_online_properties_error_cb(handle, *args))

    def _presence_update_cb(self, presence):
        """Send update for online/offline status of presence"""
        for handle in presence:
            timestamp, statuses = presence[handle]
            online = handle in self._online_contacts
            for status, params in statuses.items():
                if not online and status == "offline":
                    # weren't online in the first place...
                    continue
                jid = self._conn[CONN_INTERFACE].InspectHandles(CONNECTION_HANDLE_TYPE_CONTACT, [handle])[0]
                olstr = "ONLINE"
                if not online: olstr = "OFFLINE"
                logging.debug("Handle %s (%s) was %s, status now '%s'." % (handle, jid, olstr, status))
                if not online and status in ["available", "away", "brb", "busy", "dnd", "xa"]:
                    self._contact_online(handle)
                elif status in ["offline", "invisible"]:
                    self._contact_offline(handle)

    def _avatar_updated_cb(self, handle, new_avatar_token):
        """Handle update of given user (handle)'s avatar"""
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            # ignore network events for Owner property changes since those
            # are handled locally
            return

        if not self._online_contacts.has_key(handle):
            logging.debug("Handle %s unknown." % handle)
            return

        jid = self._online_contacts[handle]
        if not jid:
            logging.debug("Handle %s not valid yet..." % handle)
            return

        icon = self._icon_cache.get_icon(jid, new_avatar_token)
        if not icon:
            # cache miss
            avatar, mime_type = self._conn[CONN_INTERFACE_AVATARS].RequestAvatar(handle)
            icon = ''.join(map(chr, avatar))
            self._icon_cache.store_icon(jid, new_avatar_token, icon)

        self.emit("avatar-updated", handle, icon)

    def _alias_changed_cb(self, aliases):
        """Handle update of aliases for all users"""
        for handle, alias in aliases:
            prop = {'nick': alias}
            #print "Buddy %s alias changed to %s" % (handle, alias)
            if self._online_contacts.has_key(handle) and self._online_contacts[handle]:
                self._buddy_properties_changed_cb(handle, prop)

    def _buddy_properties_changed_cb(self, handle, properties):
        """Handle update of given user (handle)'s properties"""
        if handle == self._conn[CONN_INTERFACE].GetSelfHandle():
            # ignore network events for Owner property changes since those
            # are handled locally
            return
        if self._online_contacts.has_key(handle) and self._online_contacts[handle]:
            self.emit("buddy-properties-changed", handle, properties)

    def _buddy_activities_changed_cb(self, handle, activities):
        """Handle update of given user (handle)'s activities"""
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
        """Handle update of given user (handle)'s current activity"""
    
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
        """Handle creation of a new channel
        """
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
        """Request update from network on the activity properties of act_id"""
        handle = self._activities.get(act_id)
        if not handle:
            raise RuntimeError("Unknown activity %s: couldn't find handle.")

        self._conn[CONN_INTERFACE_ACTIVITY_PROPERTIES].GetProperties(handle,
                reply_handler=lambda *args: self._activity_properties_changed_cb(handle, *args),
                error_handler=lambda *args: self._log_error_cb("getting activity properties", *args))

    def set_activity_properties(self, act_id, props):
        """Send update to network on the activity properties of act_id (props)"""
        handle = self._activities.get(act_id)
        if not handle:
            raise RuntimeError("Unknown activity %s: couldn't find handle.")

        self._conn[CONN_INTERFACE_ACTIVITY_PROPERTIES].SetProperties(handle, props,
                reply_handler=self._ignore_success_cb,
                error_handler=lambda *args: self._log_error_cb("setting activity properties", *args))

    def _activity_properties_changed_cb(self, room, properties):
        """Handle update of properties for a "room" (activity handle)"""
        for act_id, act_handle in self._activities.items():
            if room == act_handle:
                self.emit("activity-properties-changed", act_id, properties)
                return
