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

import logging

import dbus
import gobject
import telepathy

_logger = logging.getLogger('sugar.presence.activity')

class Activity(gobject.GObject):
    """UI interface for an Activity in the presence service
    
    Activities in the presence service represent your and other user's
    shared activities.
    
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
                         ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
    }

    __gproperties__ = {
        'id'        : (str, None, None, None, gobject.PARAM_READABLE),
        'name'      : (str, None, None, None, gobject.PARAM_READWRITE),
        'tags'      : (str, None, None, None, gobject.PARAM_READWRITE),
        'color'     : (str, None, None, None, gobject.PARAM_READWRITE),
        'type'      : (str, None, None, None, gobject.PARAM_READABLE),
        'private'   : (bool, None, None, True, gobject.PARAM_READWRITE),
        'joined'    : (bool, None, None, False, gobject.PARAM_READABLE),
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
        self._activity.connect_to_signal('BuddyHandleJoined', 
                                         self._buddy_handle_joined_cb)
        self._activity.connect_to_signal('BuddyLeft',
                                         self._buddy_left_cb)
        self._activity.connect_to_signal('NewChannel', self._new_channel_cb)
        self._activity.connect_to_signal('PropertiesChanged',
                                         self._properties_changed_cb,
                                         utf8_strings=True)
        # FIXME: this *would* just use a normal proxy call, but I want the
        # pending call object so I can block on it, and normal proxy methods
        # don't return those as of dbus-python 0.82.1; so do it the hard way
        self._get_properties_call = bus.call_async(self._PRESENCE_SERVICE,
                object_path, self._ACTIVITY_DBUS_INTERFACE, 'GetProperties',
                '', (), self._get_properties_reply_cb,
                self._get_properties_error_cb, utf8_strings=True)

        self._id = None
        self._color = None
        self._name = None
        self._type = None
        self._tags = None
        self._private = True
        self._joined = False
        # Cache for get_buddy_by_handle, maps handles to buddy object paths
        self._handle_to_buddy_path = {}
        self._buddy_path_to_handle = {}

        # Set up by set_up_tubes()
        self.telepathy_conn = None
        self.telepathy_tubes_chan = None
        self.telepathy_text_chan = None
        self._telepathy_room = None

    def __repr__(self):
        return ('<proxy for %s at %x>' % (self._object_path, id(self)))

    def _get_properties_reply_cb(self, new_props):
        self._get_properties_call = None
        _logger.debug('%r: initial GetProperties returned', self)
        self._properties_changed_cb(new_props)

    def _get_properties_error_cb(self, e):
        self._get_properties_call = None
        # FIXME: do something with the error
        _logger.warning('%r: Error doing initial GetProperties: %s', self, e)

    def _properties_changed_cb(self, new_props):
        _logger.debug('%r: Activity properties changed to %r', self, new_props)
        val = new_props.get('name', self._name)
        if isinstance(val, str) and val != self._name:
            self._name = val
            self.notify('name')
        val = new_props.get('tags', self._tags)
        if isinstance(val, str) and val != self._tags:
            self._tags = val
            self.notify('tags')
        val = new_props.get('color', self._color)
        if isinstance(val, str) and val != self._color:
            self._color = val
            self.notify('color')
        val = bool(new_props.get('private', self._private))
        if val != self._private:
            self._private = val
            self.notify('private')
        val = new_props.get('id', self._id)
        if isinstance(val, str) and self._id is None:
            self._id = val
            self.notify('id')
        val = new_props.get('type', self._type)
        if isinstance(val, str) and self._type is None:
            self._type = val
            self.notify('type')

    def object_path(self):
        """Get our dbus object path"""
        return self._object_path

    def do_get_property(self, pspec):
        """Retrieve a particular property from our property dictionary"""

        if pspec.name == "joined":
            return self._joined

        if self._get_properties_call is not None:
            _logger.debug('%r: Blocking on GetProperties() because someone '
                          'wants property %s', self, pspec.name)
            self._get_properties_call.block()

        if pspec.name == "id":
            return self._id
        elif pspec.name == "name":
            return self._name
        elif pspec.name == "color":
            return self._color
        elif pspec.name == "type":
            return self._type
        elif pspec.name == "tags":
            return self._tags
        elif pspec.name == "private":
            return self._private

    # FIXME: need an asynchronous API to set these properties, particularly
    # 'private'
    def do_set_property(self, pspec, val):
        """Set a particular property in our property dictionary"""
        if pspec.name == "name":
            self._activity.SetProperties({'name': val})
            self._name = val
        elif pspec.name == "color":
            self._activity.SetProperties({'color': val})
            self._color = val
        elif pspec.name == "tags":
            self._activity.SetProperties({'tags': val})
            self._tags = val
        elif pspec.name == "private":
            self._activity.SetProperties({'private': val})
            self._private = val

    def set_private(self, val, reply_handler, error_handler):
        self._activity.SetProperties({'private': bool(val)},
                                     reply_handler=reply_handler,
                                     error_handler=error_handler)

    def _emit_buddy_joined_signal(self, object_path):
        """Generate buddy-joined GObject signal with presence Buddy object"""
        self.emit('buddy-joined', self._ps_new_object(object_path))
        return False

    def _buddy_handle_joined_cb(self, object_path, handle):
        _logger.debug('%r: buddy %s joined with handle %u', self, object_path,
                      handle)
        gobject.idle_add(self._emit_buddy_joined_signal, object_path)
        self._handle_to_buddy_path[handle] = object_path
        self._buddy_path_to_handle[object_path] = handle

    def _emit_buddy_left_signal(self, object_path):
        """Generate buddy-left GObject signal with presence Buddy object
        
        XXX note use of _ps_new_object instead of _ps_del_object here
        """
        self.emit('buddy-left', self._ps_new_object(object_path))
        return False

    def _buddy_left_cb(self, object_path):
        _logger.debug('%r: buddy %s left', self, object_path)
        gobject.idle_add(self._emit_buddy_left_signal, object_path)
        handle = self._buddy_path_to_handle.pop(object_path, None)
        if handle:
            self._handle_to_buddy_path.pop(handle, None)

    def _emit_new_channel_signal(self, object_path):
        """Generate new-channel GObject signal with channel object path 
        
        New telepathy-python communications channel has been opened
        """
        self.emit('new-channel', object_path)
        return False

    def _new_channel_cb(self, object_path):
        _logger.debug('%r: new channel created at %s', self, object_path)
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

    def get_buddy_by_handle(self, handle):
        """Retrieve the Buddy object given a telepathy handle.
        
        buddy object paths are cached in self._handle_to_buddy_path,
        so we can get the buddy without calling PS.
        """
        object_path = self._handle_to_buddy_path.get(handle, None)
        if object_path:
            buddy = self._ps_new_object(object_path)
            return buddy
        return None

    def invite(self, buddy, message, response_cb):
        """Invite the given buddy to join this activity.

        The callback will be called with one parameter: None on success,
        or an exception on failure.
        """
        op = buddy.object_path()
        _logger.debug('%r: inviting %s', self, op)
        self._activity.Invite(op, message,
                              reply_handler=lambda: response_cb(None),
                              error_handler=response_cb)

    # Joining and sharing (FIXME: sharing is actually done elsewhere)

    def set_up_tubes(self, reply_handler, error_handler):

        cpaths = []

        def tubes_chan_ready(chan):
            _logger.debug('%r: Tubes channel %r is ready', self, chan)
            self.telepathy_tubes_chan = chan

            _logger.debug('%r: finished setting up tubes', self)
            reply_handler()

        def got_tubes_chan(path):
            _logger.debug('%r: got Tubes channel at %s', self, path)
            telepathy.client.Channel(self.telepathy_conn.service_name,
                                     path, ready_handler=tubes_chan_ready,
                                     error_handler=error_handler)

        def text_chan_ready(chan):
            _logger.debug('%r: Text channel %r is ready', self, chan)
            self.telepathy_text_chan = chan

            self.telepathy_conn.RequestChannel(telepathy.CHANNEL_TYPE_TUBES,
                                               telepathy.HANDLE_TYPE_ROOM,
                                               self._telepathy_room_handle,
                                               True,
                                               reply_handler=got_tubes_chan,
                                               error_handler=error_handler)

        def got_text_chan(path):
            _logger.debug('%r: got Text channel at %s', self, path)
            telepathy.client.Channel(self.telepathy_conn.service_name,
                                     path, ready_handler=text_chan_ready,
                                     error_handler=error_handler)

        def conn_ready(conn):
            _logger.debug('%r: Connection %r is ready', self, conn)
            self.telepathy_conn = conn

            # For the moment we'll do this synchronously.
            # If the PS gained a GetRoom method, we could
            # do this async too

            for channel_path in cpaths:
                channel = telepathy.client.Channel(conn.service_name,
                                                   channel_path)
                handle_type, handle = channel.GetHandle()
                if handle_type == telepathy.HANDLE_TYPE_ROOM:
                    room = handle
                    break

            if room is None:
                error_handler(AssertionError("Presence Service didn't create "
                    "a chatroom"))
            else:
                self._telepathy_room_handle = room

                conn.RequestChannel(telepathy.CHANNEL_TYPE_TEXT,
                                    telepathy.HANDLE_TYPE_ROOM,
                                    room, True,
                                    reply_handler=got_text_chan,
                                    error_handler=error_handler)

        def got_channels(bus_name, conn_path, channel_paths):
            _logger.debug('%r: Connection on %s at %s, channel paths: %r',
                          self, bus_name, conn_path, channel_paths)

            # can't use assignment for this due to Python scoping
            cpaths.extend(channel_paths)

            telepathy.client.Connection(bus_name, conn_path,
                                        ready_handler=conn_ready,
                                        error_handler=error_handler)

        self._activity.GetChannels(reply_handler=got_channels,
                                   error_handler=error_handler)

    def _join_cb(self):
        _logger.debug('%r: Join finished', self)
        self._joined = True
        self.emit("joined", True, None)

    def _join_error_cb(self, err):
        _logger.debug('%r: Join failed because: %s', self, err)
        self.emit("joined", False, str(err))

    def join(self):
        """Join this activity.

        Emits 'joined' and otherwise does nothing if we're already joined.
        """
        if self._joined:
            self.emit("joined", True, None)
            return

        _logger.debug('%r: joining', self)

        def joined():
            self.set_up_tubes(reply_handler=self._join_cb,
                              error_handler=self._join_error_cb)

        self._activity.Join(reply_handler=joined,
                            error_handler=self._join_error_cb)

    # GetChannels() wrapper

    def get_channels(self):
        """Retrieve communications channel descriptions for the activity 
        
        Returns a tuple containing:
            - the D-Bus well-known service name of the connection
              (FIXME: this is redundant; in Telepathy it can be derived
              from that of the connection)
            - the D-Bus object path of the connection
            - a list of D-Bus object paths representing the channels
              associated with this activity
        """
        (bus_name, connection, channels) = self._activity.GetChannels()
        _logger.debug('%r: bus name is %s, connection is %s, channels are %r',
                      self, bus_name, connection, channels)
        return bus_name, connection, channels

    # Leaving

    def _leave_cb(self):
        """Callback for async action of leaving shared activity."""
        self.emit("joined", False, "left activity")

    def _leave_error_cb(self, err):
        """Callback for error in async leaving of shared activity."""
        _logger.debug('Failed to leave activity: %s', err)

    def leave(self):
        """Leave this shared activity"""
        _logger.debug('%r: leaving', self)
        self._joined = False
        self._activity.Leave(reply_handler=self._leave_cb,
                             error_handler=self._leave_error_cb)
