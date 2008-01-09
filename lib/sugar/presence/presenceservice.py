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

import logging

import dbus
import dbus.exceptions
import dbus.glib
import gobject

from sugar.presence.buddy import Buddy
from sugar.presence.activity import Activity


DBUS_SERVICE = "org.laptop.Sugar.Presence"
DBUS_INTERFACE = "org.laptop.Sugar.Presence"
DBUS_PATH = "/org/laptop/Sugar/Presence"

_logger = logging.getLogger('sugar.presence.presenceservice')


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
        # parameters: (activity: Activity, inviter: Buddy, message: unicode)
        'activity-invitation': (gobject.SIGNAL_RUN_FIRST, None, ([object]*3)),
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
    

    def __init__(self, allow_offline_iface=True):
        """Initialise the service and attempt to connect to events
        """
        gobject.GObject.__init__(self)
        self._objcache = {}

        # Get a connection to the session bus
        self._bus = dbus.SessionBus()
        self._bus.add_signal_receiver(self._name_owner_changed_cb,
                                    signal_name="NameOwnerChanged",
                                    dbus_interface="org.freedesktop.DBus")

        # attempt to load the interface to the service...
        self._allow_offline_iface = allow_offline_iface
        self._get_ps()

    def _name_owner_changed_cb(self, name, old, new):
        if name != DBUS_SERVICE:
            return
        if (old and len(old)) and (not new and not len(new)):
            # PS went away, clear out PS dbus service wrapper
            self._ps_ = None
        elif (not old and not len(old)) and (new and len(new)):
            # PS started up
            self._get_ps()

    _ps_ = None
    def _get_ps(self):
        """Retrieve dbus interface to PresenceService 
        
        Also registers for updates from various dbus events on the 
        interface.
        
        If unable to retrieve the interface, we will temporarily 
        return an _OfflineInterface object to allow the calling 
        code to continue functioning as though it had accessed a 
        real presence service.
        
        If successful, caches the presence service interface 
        for use by other methods and returns that interface
        """
        if not self._ps_:
            try:
                # NOTE: We need to follow_name_owner_changes here
                #       because we can not connect to a signal unless 
                #       we follow the changes or we start the service
                #       before we connect.  Starting the service here
                #       causes a major bottleneck during startup
                ps = dbus.Interface(
                    self._bus.get_object(DBUS_SERVICE,
                                         DBUS_PATH,
                                         follow_name_owner_changes=True), 
                    DBUS_INTERFACE
                )
            except dbus.exceptions.DBusException, err:
                _logger.error(
                    """Failure retrieving %r interface from the D-BUS service %r %r: %s""",
                    DBUS_INTERFACE, DBUS_SERVICE, DBUS_PATH, err
                )
                if self._allow_offline_iface:
                    return _OfflineInterface()
                raise RuntimeError("Failed to connect to the presence service.")
            else:
                self._ps_ = ps 
                ps.connect_to_signal('BuddyAppeared', self._buddy_appeared_cb)
                ps.connect_to_signal('BuddyDisappeared', self._buddy_disappeared_cb)
                ps.connect_to_signal('ActivityAppeared', self._activity_appeared_cb)
                ps.connect_to_signal('ActivityDisappeared', self._activity_disappeared_cb)
                ps.connect_to_signal('ActivityInvitation', self._activity_invitation_cb)
                ps.connect_to_signal('PrivateInvitation', self._private_invitation_cb)
        return self._ps_
        
    _ps = property(
        _get_ps, None, None,
        """DBUS interface to the PresenceService (services/presence/presenceservice)"""
    )

    def _new_object(self, object_path):
        """Turn new object path into (cached) Buddy/Activity instance
        
        object_path -- full dbus path of the new object, must be
            prefixed with either of _PS_BUDDY_OP or _PS_ACTIVITY_OP
        
        Note that this method is called throughout the class whenever
        the representation of the object is required, it is not only 
        called when the object is first discovered.  The point is to only have
        _one_ Python object for any D-Bus object represented by an object path,
        effectively wrapping the D-Bus object in a single Python GObject.
        
        returns presence Buddy or Activity representation
        """
        obj = None
        try:
            obj = self._objcache[object_path]
            _logger.debug('Reused proxy %r', obj)
        except KeyError:
            if object_path.startswith(self._PS_BUDDY_OP):
                obj = Buddy(self._bus, self._new_object,
                        self._del_object, object_path)
            elif object_path.startswith(self._PS_ACTIVITY_OP):
                obj = Activity(self._bus, self._new_object,
                        self._del_object, object_path)
                try:
                    # Pre-fill the activity's ID
                    foo = obj.props.id
                except dbus.exceptions.DBusException, err:
                    pass
            else:
                raise RuntimeError("Unknown object type")
            self._objcache[object_path] = obj
            _logger.debug('Created proxy %r', obj)
        return obj

    def _have_object(self, object_path):
        return object_path in self._objcache.keys()

    def _del_object(self, object_path):
        """Fully remove an object from the object cache when it's no longer needed.
        """
        del self._objcache[object_path]

    def _emit_buddy_appeared_signal(self, object_path):
        """Emit GObject event with presence.buddy.Buddy object"""
        self.emit('buddy-appeared', self._new_object(object_path))
        return False

    def _buddy_appeared_cb(self, op):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_buddy_appeared_signal, op)

    def _emit_buddy_disappeared_signal(self, object_path):
        """Emit GObject event with presence.buddy.Buddy object"""
        # Don't try to create a new object here if needed; it will probably
        # fail anyway because the object has already been destroyed in the PS
        if self._have_object(object_path):
            obj = self._objcache[object_path]
            self.emit('buddy-disappeared', obj)

            # We cannot maintain the object in the cache because that would keep
            # a lot of objects from being collected. That includes UI objects
            # due to signals using strong references.
            # If we want to cache some despite the memory usage increase,
            # we could use a LRU cache limited to some value.
            del self._objcache[object_path]
            obj.destroy()
            
        return False

    def _buddy_disappeared_cb(self, object_path):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_buddy_disappeared_signal, object_path)

    def _emit_activity_invitation_signal(self, activity_path, buddy_path,
                                         message):
        """Emit GObject event with presence.activity.Activity object"""
        self.emit('activity-invitation', self._new_object(activity_path),
                  self._new_object(buddy_path), unicode(message))
        return False

    def _activity_invitation_cb(self, activity_path, buddy_path, message):
        """Callback for dbus event (forwards to method to emit GObject event)"""
        gobject.idle_add(self._emit_activity_invitation_signal, activity_path,
                         buddy_path, message)

    def _emit_private_invitation_signal(self, bus_name, connection, channel):
        """Emit GObject event with bus_name, connection and channel"""
        self.emit('private-invitation', bus_name, connection, channel)
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
        """Return the Buddy or Activity object corresponding to the given
        D-Bus object path.
        """
        return self._new_object(object_path)

    def get_activities(self):
        """Retrieve set of all activities from service
        
        returns list of Activity objects for all object paths
            the service reports exist (using GetActivities)
        """
        try:
            resp = self._ps.GetActivities()
        except dbus.exceptions.DBusException, err:
            _logger.warn(
                """Unable to retrieve activity list from presence service: %s"""
                % err
            )
            return []
        else:
            acts = []
            for item in resp:
                acts.append(self._new_object(item))
            return acts

    def _get_activities_cb(self, reply_handler, resp):
        acts = []
        for item in resp:
            acts.append(self._new_object(item))

        reply_handler(acts)

    def _get_activities_error_cb(self, error_handler, e):
        if error_handler:
            error_handler(e)
        else:
            _logger.warn(
                """Unable to retrieve activity-list from presence service: %s"""
                % e
            )

    def get_activities_async(self, reply_handler=None, error_handler=None):
        """Retrieve set of all activities from service asyncronously 
        """

        if not reply_handler:
            logging.error('Function get_activities_async called without a reply handler. Can not run.') 
            return

        self._ps.GetActivities(
             reply_handler=lambda resp:self._get_activities_cb(reply_handler, resp),
             error_handler=lambda e:self._get_activities_error_cb(error_handler, e))


    def get_activity(self, activity_id, warn_if_none=True):
        """Retrieve single Activity object for the given unique id

        activity_id -- unique ID for the activity

        returns single Activity object or None if the activity
            is not found using GetActivityById on the service
        """
        try:
            act_op = self._ps.GetActivityById(activity_id)
        except dbus.exceptions.DBusException, err:
            if warn_if_none:
                _logger.warn("Unable to retrieve activity handle for %r from "
                             "presence service: %s", activity_id, err)
            return None
        return self._new_object(act_op)

    def get_buddies(self):
        """Retrieve set of all buddies from service
        
        returns list of Buddy objects for all object paths
            the service reports exist (using GetBuddies)
        """
        try:
            resp = self._ps.GetBuddies()
        except dbus.exceptions.DBusException, err:
            _logger.warn(
                """Unable to retrieve buddy-list from presence service: %s"""
                % err
            )
            return []
        else:
            buddies = []
            for item in resp:
                buddies.append(self._new_object(item))
            return buddies

    def _get_buddies_cb(self, reply_handler, resp):
        buddies = []
        for item in resp:
            buddies.append(self._new_object(item))

        reply_handler(buddies)

    def _get_buddies_error_cb(self, error_handler, e):
        if error_handler:
            error_handler(e)
        else:
            _logger.warn(
                """Unable to retrieve buddy-list from presence service: %s"""
                % e
            )

    def get_buddies_async(self, reply_handler=None, error_handler=None):
        """Retrieve set of all buddies from service asyncronously 
        """

        if not reply_handler:
            logging.error('Function get_buddies_async called without a reply handler. Can not run.') 
            return

        self._ps.GetBuddies(
             reply_handler=lambda resp:self._get_buddies_cb(reply_handler, resp),
             error_handler=lambda e:self._get_buddies_error_cb(error_handler, e))

    def get_buddy(self, key):
        """Retrieve single Buddy object for the given public key
        
        key -- buddy's public encryption key
        
        returns single Buddy object or None if the activity 
            is not found using GetBuddyByPublicKey on the 
            service
        """
        try:
            buddy_op = self._ps.GetBuddyByPublicKey(dbus.ByteArray(key))
        except dbus.exceptions.DBusException, err:
            _logger.warn(
                """Unable to retrieve buddy handle for %r from presence service: %s"""
                % key, err
            )
            return None
        return self._new_object(buddy_op)

    def get_buddy_by_telepathy_handle(self, tp_conn_name, tp_conn_path,
                                      handle):
        """Retrieve single Buddy object for the given public key

        :Parameters:
            `tp_conn_name` : str
                The well-known bus name of a Telepathy connection
            `tp_conn_path` : dbus.ObjectPath
                The object path of the Telepathy connection
            `handle` : int or long
                The handle of a Telepathy contact on that connection,
                of type HANDLE_TYPE_CONTACT. This may not be a
                channel-specific handle.
        :Returns: the Buddy object, or None if the buddy is not found
        """
        try:
            buddy_op = self._ps.GetBuddyByTelepathyHandle(tp_conn_name,
                                                          tp_conn_path,
                                                          handle)
        except dbus.exceptions.DBusException, err:
            _logger.warn('Unable to retrieve buddy handle for handle %u at '
                         'conn %s:%s from presence service: %s',
                         handle, tp_conn_name, tp_conn_path, err)
            return None
        return self._new_object(buddy_op)

    def get_owner(self):
        """Retrieves the laptop "owner" Buddy object."""
        try:
            owner_op = self._ps.GetOwner()
        except dbus.exceptions.DBusException, err:
            _logger.warn(
                """Unable to retrieve local user/owner from presence service: %s"""
                % err
            )
            raise RuntimeError("Could not get owner object from presence service.")
        return self._new_object(owner_op)

    def _share_activity_cb(self, activity, op):
        """Finish sharing the activity
        """
        psact = self._new_object(op)
        psact._joined = True
        _logger.debug('%r: Just shared, setting up tubes', activity)
        psact.set_up_tubes(reply_handler=lambda:
                            self.emit("activity-shared", True, psact, None),
                           error_handler=lambda e:
                            self._share_activity_error_cb(activity, e))

    def _share_activity_error_cb(self, activity, err):
        """Notify with GObject event of unsuccessful sharing of activity"""
        _logger.debug("Error sharing activity %s: %s" % (activity.get_id(), err))
        self.emit("activity-shared", False, None, err)

    def share_activity(self, activity, properties={}, private=True):
        """Ask presence service to ask the activity to share itself publicly.
        
        Uses the AdvertiseActivity method on the service to ask for the 
        sharing of the given activity.  Arranges to emit activity-shared 
        event with:
        
            (success, Activity, err)
        
        on success/failure.
        
        returns None
        """
        actid = activity.get_id()

        # Ensure the activity is not already shared/joined
        for obj in self._objcache.values():
            if not isinstance(object, Activity):
                continue
            if obj.props.id == actid or obj.props.joined:
                raise RuntimeError("Activity %s is already shared." %
                                   actid)

        atype = activity.get_bundle_id()
        name = activity.props.title
        properties['private'] = bool(private)
        self._ps.ShareActivity(actid, atype, name, properties,
                reply_handler=lambda op: \
                    self._share_activity_cb(activity, op),
                error_handler=lambda e: \
                    self._share_activity_error_cb(activity, e))

    def get_preferred_connection(self):
        """Gets the preferred telepathy connection object that an activity
        should use when talking directly to telepathy

        returns the bus name and the object path of the Telepathy connection"""

        try:
            bus_name, object_path = self._ps.GetPreferredConnection()
        except dbus.exceptions.DBusException:
            return None

        return bus_name, object_path

class _OfflineInterface( object ):
    """Offline-presence-service interface
    
    Used to mimic the behaviour of a real PresenceService sufficiently
    to avoid crashing client code that expects the given interface.
    
    XXX we could likely return a "MockOwner" object reasonably 
    easily, but would it be worth it?
    """
    def raiseException( self, *args, **named ):
        """Raise dbus.exceptions.DBusException"""
        raise dbus.exceptions.DBusException( 
            """PresenceService Interface not available"""
        )
    GetActivities = raiseException
    GetActivityById = raiseException
    GetBuddies = raiseException
    GetBuddyByPublicKey = raiseException
    GetOwner = raiseException
    GetPreferredConnection = raiseException
    def ShareActivity( 
        self, actid, atype, name, properties,
        reply_handler, error_handler,
    ):
        """Pretend to share and fail..."""
        exc = IOError(
            """Unable to share activity as PresenceService is not currenly available"""
        )
        return error_handler( exc )

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
def get_instance(allow_offline_iface=False):
    """Retrieve this process' view of the PresenceService"""
    global _ps
    if not _ps:
        _ps = PresenceService(allow_offline_iface)
    return _ps

