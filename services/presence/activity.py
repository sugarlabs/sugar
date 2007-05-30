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
import dbus.service
from dbus.gobject_service import ExportedGObject
from sugar import util
import logging

from telepathy.constants import CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES
from telepathy.interfaces import (CHANNEL_INTERFACE, CHANNEL_INTERFACE_GROUP)

_ACTIVITY_PATH = "/org/laptop/Sugar/Presence/Activities/"
_ACTIVITY_INTERFACE = "org.laptop.Sugar.Presence.Activity"

_PROP_ID = "id"
_PROP_NAME = "name"
_PROP_COLOR = "color"
_PROP_TYPE = "type"
_PROP_VALID = "valid"
_PROP_LOCAL = "local"
_PROP_JOINED = "joined"
_PROP_CUSTOM_PROPS = "custom-props"

_logger = logging.getLogger('s-p-s.activity')

class Activity(ExportedGObject):
    """Represents a shared activity seen on the network, or a local activity
    that has been, or will be, shared onto the network.

    The activity might be public, restricted to a group, or invite-only.
    """

    __gtype_name__ = "Activity"

    __gsignals__ = {
        'validity-changed':
            # The activity's validity has changed.
            # An activity is valid if its name, color, type and ID have been
            # set.
            # Arguments:
            #   validity: bool
            (gobject.SIGNAL_RUN_FIRST, None, [bool]),
        'disappeared':
            # Nobody is in this activity any more.
            # No arguments.
            (gobject.SIGNAL_RUN_FIRST, None, []),
    }

    __gproperties__ = {
        _PROP_ID           : (str, None, None, None,
                              gobject.PARAM_READWRITE |
                              gobject.PARAM_CONSTRUCT_ONLY),
        _PROP_NAME         : (str, None, None, None, gobject.PARAM_READWRITE),
        _PROP_COLOR        : (str, None, None, None, gobject.PARAM_READWRITE),
        _PROP_TYPE         : (str, None, None, None, gobject.PARAM_READWRITE),
        _PROP_VALID        : (bool, None, None, False, gobject.PARAM_READABLE),
        _PROP_LOCAL        : (bool, None, None, False,
                              gobject.PARAM_READWRITE |
                              gobject.PARAM_CONSTRUCT_ONLY),
        _PROP_JOINED       : (bool, None, None, False, gobject.PARAM_READABLE),
        _PROP_CUSTOM_PROPS : (object, None, None,
                              gobject.PARAM_READWRITE |
                              gobject.PARAM_CONSTRUCT_ONLY)
    }

    _RESERVED_PROPNAMES = __gproperties__.keys()

    def __init__(self, bus, object_id, ps, tp, **kwargs):
        """Initializes the activity and sets its properties to default values.

        :Parameters:
            `bus` : dbus.bus.BusConnection
                A connection to the D-Bus session bus
            `object_id` : int
                PS ID for this activity, used to construct the object-path
            `ps` : presenceservice.PresenceService
                The presence service
            `tp` : server plugin
                The server plugin object (stands for "telepathy plugin")
        :Keywords:
            `id` : str
                The globally unique activity ID (required)
            `name` : str
                Human-readable title for the activity
            `color` : str
                Activity color in #RRGGBB,#RRGGBB (stroke,fill) format
            `type` : str
                D-Bus service name representing the activity type
            `local : bool
                If True, this activity was initiated locally and is not
                (yet) advertised on the network
                (FIXME: is this description right?)
            `custom-props` : dict
                Activity-specific properties
        """

        if not object_id or not isinstance(object_id, int):
            raise ValueError("object id must be a valid number")
        if not tp:
            raise ValueError("telepathy CM must be valid")

        self._ps = ps
        self._object_id = object_id
        self._object_path = dbus.ObjectPath(_ACTIVITY_PATH +
                                            str(self._object_id))

        self._buddies = set()
        self._member_handles = set()
        self._joined = False

        # the telepathy client
        self._tp = tp
        self._self_handle = None
        self._text_channel = None
        self._text_channel_group_flags = 0

        self._valid = False
        self._id = None
        self._actname = None
        self._color = None
        self._local = False
        self._type = None
        self._custom_props = {}

        # ensure no reserved property names are in custom properties
        cprops = kwargs.get(_PROP_CUSTOM_PROPS)
        if cprops is not None:
            (rprops, cprops) = self._split_properties(cprops)
            if len(rprops.keys()) > 0:
                raise ValueError("Cannot use reserved property names '%s'"
                                 % ", ".join(rprops.keys()))

        if not kwargs.get(_PROP_ID):
            raise ValueError("activity id is required")
        if not util.validate_activity_id(kwargs[_PROP_ID]):
            raise ValueError("Invalid activity id '%s'" % kwargs[_PROP_ID])

        ExportedGObject.__init__(self, bus, self._object_path,
                                 gobject_properties=kwargs)
        if self.props.local and not self.props.valid:
            raise RuntimeError("local activities require color, type, and "
                               "name")

        # If not yet valid, query activity properties
        if not self.props.valid:
            tp.update_activity_properties(self._id)

    def do_get_property(self, pspec):
        """Gets the value of a property associated with this activity.

        pspec -- Property specifier

        returns The value of the given property.
        """

        if pspec.name == _PROP_ID:
            return self._id
        elif pspec.name == _PROP_NAME:
            return self._actname
        elif pspec.name == _PROP_COLOR:
            return self._color
        elif pspec.name == _PROP_TYPE:
            return self._type
        elif pspec.name == _PROP_VALID:
            return self._valid
        elif pspec.name == _PROP_JOINED:
            return self._joined
        elif pspec.name == _PROP_LOCAL:
            return self._local

    def do_set_property(self, pspec, value):
        """Sets the value of a property associated with this activity.

        pspec -- Property specifier
        value -- Desired value

        Note that the "type" property can be set only once; attempting to set
        it to something different later will raise a RuntimeError.

        """
        if pspec.name == _PROP_ID:
            if self._id:
                raise RuntimeError("activity ID is already set")
            self._id = value
        elif pspec.name == _PROP_NAME:
            self._actname = value
        elif pspec.name == _PROP_COLOR:
            self._color = value
        elif pspec.name == _PROP_TYPE:
            if self._type:
                raise RuntimeError("activity type is already set")
            self._type = value
        elif pspec.name == _PROP_JOINED:
            self._joined = value
        elif pspec.name == _PROP_LOCAL:
            self._local = value
        elif pspec.name == _PROP_CUSTOM_PROPS:
            if not value:
                value = {}
            (rprops, cprops) = self._split_properties(value)
            self._custom_props = {}
            for (key, dvalue) in cprops.items():
                self._custom_props[str(key)] = str(dvalue)

        self._update_validity()

    def _update_validity(self):
        """Sends a "validity-changed" signal if this activity's validity has
        changed.

        Determines whether this activity's status has changed from valid to
        invalid, or invalid to valid, and emits a "validity-changed" signal
        if either is true.  "Valid" means that the object's type, ID, name,
        colour and type properties have all been set to something valid
        (i.e., not "None").

        """
        try:
            old_valid = self._valid
            if self._color and self._actname and self._id and self._type:
                self._valid = True
            else:
                self._valid = False

            if old_valid != self._valid:
                self.emit("validity-changed", self._valid)
        except AttributeError:
            self._valid = False

    # dbus signals
    @dbus.service.signal(_ACTIVITY_INTERFACE,
                        signature="o")
    def BuddyJoined(self, buddy_path):
        """Generates DBUS signal when a buddy joins this activity.

        buddy_path -- DBUS path to buddy object
        """
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE,
                        signature="o")
    def BuddyLeft(self, buddy_path):
        """Generates DBUS signal when a buddy leaves this activity.

        buddy_path -- DBUS path to buddy object
        """
        pass

    @dbus.service.signal(_ACTIVITY_INTERFACE,
                        signature="o")
    def NewChannel(self, channel_path):
        """Generates DBUS signal when a new channel is created for this
        activity.

        channel_path -- DBUS path to new channel

        XXX - what is this supposed to do?  Who is supposed to call it?
        What is the channel path?  Right now this is never called.

        """
        pass

    # dbus methods
    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetId(self):
        """DBUS method to get this activity's (randomly generated) unique ID

        :Returns: Activity ID as a string
        """
        return self.props.id

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetColor(self):
        """DBUS method to get this activity's colour

        :Returns: Activity colour as a string in the format #RRGGBB,#RRGGBB
        """
        return self.props.color

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetType(self):
        """DBUS method to get this activity's type

        :Returns: Activity type as a string, in the same form as a D-Bus
            well-known name
        """
        return self.props.type

    @dbus.service.method(_ACTIVITY_INTERFACE,
                         in_signature="", out_signature="",
                         async_callbacks=('async_cb', 'async_err_cb'))
    def Join(self, async_cb, async_err_cb):
        """DBUS method to for the local user to attempt to join the activity

        async_cb -- Callback method to be called if join attempt is successful
        async_err_cb -- Callback method to be called if join attempt is
                        unsuccessful

        """
        self.join(async_cb, async_err_cb)

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedBuddies(self):
        """DBUS method to return a list of valid buddies who are joined in
        this activity

        :Returns:
            A list of buddy object paths corresponding to those buddies
            in this activity who are 'valid' (i.e. for whom we have complete
            information)
        """
        ret = []
        for buddy in self._buddies:
            if buddy.props.valid:
                ret.append(buddy.object_path())
        return ret

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="soao")
    def GetChannels(self):
        """DBUS method to get the list of channels associated with this
        activity

        :Returns:
            a tuple containing:
                - the D-Bus well-known service name of the connection
                  (FIXME: this is redundant; in Telepathy it can be derived
                  from that of the connection)
                - the D-Bus object path of the connection
                - a list of D-Bus object paths representing the channels
                  associated with this activity
        """
        return self.get_channels()

    @dbus.service.method(_ACTIVITY_INTERFACE,
                        in_signature="", out_signature="s")
    def GetName(self):
        """DBUS method to get this activity's name

        returns Activity name
        """
        return self.props.name

    # methods
    def object_path(self):
        """Retrieves our dbus.ObjectPath object

        returns DBUS ObjectPath object
        """
        return self._object_path

    def get_joined_buddies(self):
        """Local method to return a list of valid buddies who are joined in
        this activity

        This method is called by the PresenceService on the local machine.

        returns A list of buddy objects
        """
        ret = []
        for buddy in self._buddies:
            if buddy.props.valid:
                ret.append(buddy)
        return ret

    def buddy_apparently_joined(self, buddy):
        """Adds a buddy to this activity and sends a BuddyJoined signal,
        unless we can already see who's in the activity by being in it
        ourselves.

        buddy -- Buddy object representing the buddy being added

        Adds a buddy to this activity if the buddy is not already in the
        buddy list.

        If this activity is "valid", a BuddyJoined signal is also sent.
        This method is called by the PresenceService on the local machine.

        """
        if not self._joined:
            self._add_buddies((buddy,))

    def _add_buddies(self, buddies):
        buddies = set(buddies)

        # disregard any who are already there
        buddies -= self._buddies

        self._buddies |= buddies

        for buddy in buddies:
            buddy.add_activity(self)
            if self.props.valid:
                self.BuddyJoined(buddy.object_path())

    def _remove_buddies(self, buddies):
        buddies = set(buddies)

        # disregard any who are not already there
        buddies &= self._buddies

        self._buddies -= buddies

        for buddy in buddies:
            buddy.remove_activity(self)
            if self.props.valid:
                self.BuddyJoined(buddy.object_path())

        if not self._buddies:
            self.emit('disappeared')

    def buddy_apparently_left(self, buddy):
        """Removes a buddy from this activity and sends a BuddyLeft signal,
        unless we can already see who's in the activity by being in it
        ourselves.

        buddy -- Buddy object representing the buddy being removed

        Removes a buddy from this activity if the buddy is in the buddy list.
        If this activity is "valid", a BuddyLeft signal is also sent.
        This method is called by the PresenceService on the local machine.
        """
        if not self._joined:
            self._remove_buddies((buddy,))

    def _text_channel_group_flags_changed_cb(self, flags):
        self._text_channel_group_flags = flags

    def _handle_share_join(self, tp, text_channel):
        """Called when a join to a network activity was successful.

        Called by the _shared_cb and _joined_cb methods.
        """
        if not text_channel:
            _logger.debug("Error sharing: text channel was None, shouldn't "
                          "happen")
            raise RuntimeError("Plugin returned invalid text channel")

        self._text_channel = text_channel
        self._text_channel[CHANNEL_INTERFACE].connect_to_signal('Closed',
                self._text_channel_closed_cb)
        if CHANNEL_INTERFACE_GROUP in self._text_channel:
            group = self._text_channel[CHANNEL_INTERFACE_GROUP]

            # FIXME: make these method calls async?

            group.connect_to_signal('GroupFlagsChanged',
                                    self._text_channel_group_flags_changed_cb)
            self._text_channel_group_flags = group.GetGroupFlags()

            self._self_handle = group.GetSelfHandle()

            # by the time we hook this, we need to know the group flags
            group.connect_to_signal('MembersChanged',
                                    self._text_channel_members_changed_cb)
            # bootstrap by getting the current state. This is where we find
            # out whether anyone was lying to us in their PEP info
            members = set(group.GetMembers())
            added = members - self._member_handles
            removed = self._member_handles - members
            if added or removed:
                self._text_channel_members_changed_cb('', added, removed,
                                                      (), (), 0, 0)

            # if we can see any member handles, we're probably able to see
            # all members, so can stop caring about PEP announcements for this
            # activity
            self._joined = (self._self_handle in self._member_handles)
        else:
            self._joined = True

        return True

    def _shared_cb(self, tp, activity_id, text_channel, exc, userdata):
        """XXX - not documented yet
        """
        if activity_id != self.props.id:
            # Not for us
            return

        (sigid, owner, async_cb, async_err_cb) = userdata
        self._tp.disconnect(sigid)

        if exc:
            _logger.debug("Share of activity %s failed: %s" % (self._id, exc))
            async_err_cb(exc)
        else:
            self._handle_share_join(tp, text_channel)
            self.send_properties()
            owner.add_activity(self)
            async_cb(dbus.ObjectPath(self._object_path))
            _logger.debug("Share of activity %s succeeded." % self._id)

    def _share(self, (async_cb, async_err_cb), owner):
        """XXX - not documented yet

        XXX - This method is called externally by the PresenceService
        despite the fact that this is supposed to be an internal method!
        """
        _logger.debug("Starting share of activity %s" % self._id)
        if self._joined:
            async_err_cb(RuntimeError("Already shared activity %s"
                                      % self.props.id))
            return
        sigid = self._tp.connect('activity-shared', self._shared_cb)
        self._tp.share_activity(self.props.id, (sigid, owner, async_cb,
                                                async_err_cb))
        _logger.debug("done with share attempt %s" % self._id)

    def _joined_cb(self, tp, activity_id, text_channel, exc, userdata):
        """XXX - not documented yet
        """
        if activity_id != self.props.id:
            # Not for us
            return

        (sigid, async_cb, async_err_cb) = userdata
        self._tp.disconnect(sigid)

        if exc:
            async_err_cb(exc)
        else:
            self._handle_share_join(tp, text_channel)
            async_cb()

    def join(self, async_cb, async_err_cb):
        """Local method for the local user to attempt to join the activity.

        async_cb -- Callback method to be called if join attempt is successful
        async_err_cb -- Callback method to be called if join attempt is
                        unsuccessful

        The two callbacks are passed to the server_plugin ("tp") object,
        which in turn passes them back as parameters in a callback to the
        _joined_cb method; this callback is set up within this method.
        """
        if self._joined:
            async_err_cb(RuntimeError("Already joined activity %s"
                                      % self.props.id))
            return
        sigid = self._tp.connect('activity-joined', self._joined_cb)
        self._tp.join_activity(self.props.id, (sigid, async_cb, async_err_cb))

    def get_channels(self):
        """Local method to get the list of channels associated with this
        activity

        returns XXX - expected a list of channels, instead returning a tuple?
        """
        conn = self._tp.get_connection()
        # FIXME add tubes and others channels
        return (str(conn.service_name), conn.object_path,
                [self._text_channel.object_path])

    def leave(self):
        """Local method called when the user wants to leave the activity.

        (XXX - doesn't appear to be called anywhere!)

        """
        if self._joined:
            self._text_channel[CHANNEL_INTERFACE].Close()

    def _text_channel_members_changed_cb(self, message, added, removed,
                                         local_pending, remote_pending,
                                         actor, reason):
        # Note: D-Bus calls this with list arguments, but after GetMembers()
        # we call it with set and tuple arguments; we cope with any iterable.

        if (self._text_channel_group_flags &
            CHANNEL_GROUP_FLAG_CHANNEL_SPECIFIC_HANDLES):
            map_chan = self._text_channel
        else:
            # we have global handles here
            map_chan = None

        # disregard any who are already there
        added = set(added)
        added -= self._member_handles
        self._member_handles |= added

        # for added people, we need a Buddy object
        added_buddies = self._ps.map_handles_to_buddies(self._tp,
                                                        map_chan,
                                                        added)
        self._add_buddies(added_buddies.itervalues())

        # we treat all pending members as if they weren't there
        removed = set(removed)
        removed |= set(local_pending)
        removed |= set(remote_pending)
        # disregard any who aren't already there
        removed &= self._member_handles
        self._member_handles -= removed

        # for removed people, don't bother creating a Buddy just so we can
        # say it left. If we don't already have a Buddy object for someone,
        # then obviously they're not in self._buddies!
        removed_buddies = self._ps.map_handles_to_buddies(self._tp,
                                                          map_chan,
                                                          removed,
                                                          create=False)
        self._remove_buddies(removed_buddies.itervalues())

        # if we were among those removed, we'll have to start believing
        # the spoofable PEP-based activity tracking again.
        if self._self_handle not in self._member_handles:
            self._joined = False

    def _text_channel_closed_cb(self):
        """Callback method called when the text channel is closed.

        This callback is set up in the _handle_share_join method.
        """
        self._joined = False
        self._self_handle = None
        self._text_channel = None

    def send_properties(self):
        """Tells the Telepathy server what the properties of this activity are.

        """
        props = {}
        props['name'] = self._actname
        props['color'] = self._color
        props['type'] = self._type

        # Add custom properties
        for (key, value) in self._custom_props.items():
            props[key] = value

        self._tp.set_activity_properties(self.props.id, props)

    def set_properties(self, properties):
        """Sets name, colour and/or type properties for this activity all
        at once.

        properties - Dictionary object containing properties keyed by
                     property names

        Note that if any of the name, colour and/or type property values is
        changed from what it originally was, the update_validity method will
        be called, resulting in a "validity-changed" signal being generated.
        Called by the PresenceService on the local machine.
        """
        changed  = False
        # split reserved properties from activity-custom properties
        (rprops, cprops) = self._split_properties(properties)
        if _PROP_NAME in rprops.keys():
            name = rprops[_PROP_NAME]
            if name != self._actname:
                self._actname = name
                changed = True

        if _PROP_COLOR in rprops.keys():
            color = rprops[_PROP_COLOR]
            if color != self._color:
                self._color = color
                changed = True

        if _PROP_TYPE in rprops.keys():
            type = rprops[_PROP_TYPE]
            if type != self._type:
                # Type can never be changed after first set
                if self._type:
                    _logger.debug("Activity type changed by network; this "
                                  "is illegal")
                else:
                    self._type = type
                    changed = True

        # Set custom properties
        if len(cprops.keys()) > 0:
            self.props.custom_props = cprops

        if changed:
            self._update_validity()

    def _split_properties(self, properties):
        """Extracts reserved properties.

        properties - Dictionary object containing properties keyed by
                     property names

        returns a tuple of 2 dictionaries, reserved properties and custom
        properties
        """
        rprops = {}
        cprops = {}
        for (key, value) in properties.items():
            if key in self._RESERVED_PROPNAMES:
                rprops[key] = value
            else:
                cprops[key] = value
        return (rprops, cprops)
