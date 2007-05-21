"""An "actor" on the network, whether remote or local"""
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

import os
import gobject
import dbus
import dbus.service
from dbus.gobject_service import ExportedGObject
from ConfigParser import ConfigParser, NoOptionError
import psutils

from sugar import env, profile, util
import logging
import random

_BUDDY_PATH = "/org/laptop/Sugar/Presence/Buddies/"
_BUDDY_INTERFACE = "org.laptop.Sugar.Presence.Buddy"
_OWNER_INTERFACE = "org.laptop.Sugar.Presence.Buddy.Owner"

class NotFoundError(dbus.DBusException):
    """Raised when a given actor is not found on the network"""
    def __init__(self):
        dbus.DBusException.__init__(self)
        self._dbus_error_name = _PRESENCE_INTERFACE + '.NotFound'

_PROP_NICK = "nick"
_PROP_KEY = "key"
_PROP_ICON = "icon"
_PROP_CURACT = "current-activity"
_PROP_COLOR = "color"
_PROP_OWNER = "owner"
_PROP_VALID = "valid"

# Will go away soon
_PROP_IP4_ADDRESS = "ip4-address"

_logger = logging.getLogger('s-p-s.buddy')


class Buddy(ExportedGObject):
    """Person on the network (tracks properties and shared activites)
    
    The Buddy is a collection of metadata describing a particular
    actor/person on the network.  The Buddy object tracks a set of
    activities which the actor has shared with the presence service.
    
    Buddies have a "valid" property which is used to flag Buddies
    which are no longer reachable.  That is, a Buddy may represent
    a no-longer reachable target on the network.
    
    The Buddy emits GObject events that the PresenceService uses 
    to track changes in its status.
    
    Attributes:
    
        _activities -- dictionary mapping activity ID to 
            activity.Activity objects 
        handles -- dictionary mapping telepresence client to 
            "handle" (XXX what's that)
    """

    __gsignals__ = {
        'validity-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_BOOLEAN])),
        'property-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_PYOBJECT])),
        'icon-changed':     (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_PYOBJECT]))
    }

    __gproperties__ = {
        _PROP_KEY          : (str, None, None, None,
                              gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT_ONLY),
        _PROP_ICON         : (object, None, None, gobject.PARAM_READWRITE),
        _PROP_NICK         : (str, None, None, None, gobject.PARAM_READWRITE),
        _PROP_COLOR        : (str, None, None, None, gobject.PARAM_READWRITE),
        _PROP_CURACT       : (str, None, None, None, gobject.PARAM_READWRITE),
        _PROP_VALID        : (bool, None, None, False, gobject.PARAM_READABLE),
        _PROP_OWNER        : (bool, None, None, False, gobject.PARAM_READABLE),
        _PROP_IP4_ADDRESS  : (str, None, None, None, gobject.PARAM_READWRITE)
    }

    def __init__(self, bus_name, object_id, **kwargs):
        """Initialize the Buddy object 
        
        bus_name -- DBUS object bus name (identifier)
        object_id -- the activity's unique identifier 
        kwargs -- used to initialize the object's properties
        
        constructs a DBUS "object path" from the _BUDDY_PATH
        and object_id
        """
        if not bus_name:
            raise ValueError("DBus bus name must be valid")
        if not object_id or not isinstance(object_id, int):
            raise ValueError("object id must be a valid number")

        self._bus_name = bus_name
        self._object_id = object_id
        self._object_path = _BUDDY_PATH + str(self._object_id)

        self._activities = {}   # Activity ID -> Activity
        self._activity_sigids = {}
        self.handles = {} # tp client -> handle

        self._valid = False
        self._owner = False
        self._key = None
        self._icon = ''
        self._current_activity = None
        self._nick = None
        self._color = None
        self._ip4_address = None

        if not kwargs.get(_PROP_KEY):
            raise ValueError("key required")

        _ALLOWED_INIT_PROPS = [_PROP_NICK, _PROP_KEY, _PROP_ICON, _PROP_CURACT, _PROP_COLOR, _PROP_IP4_ADDRESS]
        for (key, value) in kwargs.items():
            if key not in _ALLOWED_INIT_PROPS:
                _logger.debug("Invalid init property '%s'; ignoring..." % key)
                del kwargs[key]

        # Set icon after superclass init, because it sends DBus and GObject
        # signals when set
        icon_data = None
        if kwargs.has_key(_PROP_ICON):
            icon_data = kwargs[_PROP_ICON]
            del kwargs[_PROP_ICON]

        ExportedGObject.__init__(self, bus_name, self._object_path,
                                 gobject_properties=kwargs)

        if icon_data:
            self.props.icon = icon_data

    def do_get_property(self, pspec):
        """Retrieve current value for the given property specifier
        
        pspec -- property specifier with a "name" attribute
        """
        if pspec.name == _PROP_KEY:
            return self._key
        elif pspec.name == _PROP_ICON:
            return self._icon
        elif pspec.name == _PROP_NICK:
            return self._nick
        elif pspec.name == _PROP_COLOR:
            return self._color
        elif pspec.name == _PROP_CURACT:
            if not self._current_activity:
                return None
            if not self._activities.has_key(self._current_activity):
                return None
            return self._current_activity
        elif pspec.name == _PROP_VALID:
            return self._valid
        elif pspec.name == _PROP_OWNER:
            return self._owner
        elif pspec.name == _PROP_IP4_ADDRESS:
            return self._ip4_address

    def do_set_property(self, pspec, value):
        """Set given property 
        
        pspec -- property specifier with a "name" attribute
        value -- value to set
        
        emits 'icon-changed' signal on icon setting
        calls _update_validity on all calls
        """
        if pspec.name == _PROP_ICON:
            if str(value) != self._icon:
                self._icon = str(value)
                self.IconChanged(self._icon)
                self.emit('icon-changed', self._icon)
        elif pspec.name == _PROP_NICK:
            self._nick = value
        elif pspec.name == _PROP_COLOR:
            self._color = value
        elif pspec.name == _PROP_CURACT:
            self._current_activity = value
        elif pspec.name == _PROP_KEY:
            if self._key:
                raise RuntimeError("Key already set.")
            self._key = value
        elif pspec.name == _PROP_IP4_ADDRESS:
            self._ip4_address = value

        self._update_validity()

    # dbus signals
    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="ay")
    def IconChanged(self, icon_data):
        """Generates DBUS signal with icon_data"""

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="o")
    def JoinedActivity(self, activity_path):
        """Generates DBUS signal when buddy joins activity
        
        activity_path -- DBUS path to the activity object
        """

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="o")
    def LeftActivity(self, activity_path):
        """Generates DBUS signal when buddy leaves activity
        
        activity_path -- DBUS path to the activity object
        """

    @dbus.service.signal(_BUDDY_INTERFACE,
                        signature="a{sv}")
    def PropertyChanged(self, updated):
        """Generates DBUS signal when buddy's property changes
        
        updated -- updated property-set (dictionary) with the
            Buddy's property (changed) values. Note: not the 
            full set of properties, just the changes.
        """

    # dbus methods
    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="ay")
    def GetIcon(self):
        """Retrieve Buddy's icon data
        
        returns empty string or dbus.ByteArray
        """
        if not self.props.icon:
            return ""
        return dbus.ByteArray(self.props.icon)

    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="ao")
    def GetJoinedActivities(self):
        """Retrieve set of Buddy's joined activities (paths)
        
        returns list of dbus service paths for the Buddy's joined 
            activities
        """
        acts = []
        for act in self.get_joined_activities():
            if act.props.valid:
                acts.append(act.object_path())
        return acts

    @dbus.service.method(_BUDDY_INTERFACE,
                        in_signature="", out_signature="a{sv}")
    def GetProperties(self):
        """Retrieve set of Buddy's properties 
        
        returns dictionary of
            nick : str(nickname)
            owner : bool( whether this Buddy is an owner??? )
                XXX what is the owner flag for?
            key : str(public-key)
            color: Buddy's icon colour
                XXX what type?
            current-activity: Buddy's current activity_id, or 
                "" if no current activity
        """
        props = {}
        props[_PROP_NICK] = self.props.nick
        props[_PROP_OWNER] = self.props.owner
        props[_PROP_KEY] = self.props.key
        props[_PROP_COLOR] = self.props.color

        if self.props.ip4_address:
            props[_PROP_IP4_ADDRESS] = self.props.ip4_address
        else:
            props[_PROP_IP4_ADDRESS] = ""

        if self.props.current_activity:
            props[_PROP_CURACT] = self.props.current_activity
        else:
            props[_PROP_CURACT] = ""
        return props

    # methods
    def object_path(self):
        """Retrieve our dbus.ObjectPath object"""
        return dbus.ObjectPath(self._object_path)

    def _activity_validity_changed_cb(self, activity, valid):
        """Join or leave the activity when its validity changes"""
        if valid:
            self.JoinedActivity(activity.object_path())
        else:
            self.LeftActivity(activity.object_path())

    def add_activity(self, activity):
        """Add an activity to the Buddy's set of activities
        
        activity -- activity.Activity instance
        
        calls JoinedActivity
        """
        actid = activity.props.id
        if self._activities.has_key(actid):
            return
        self._activities[actid] = activity
        # join/leave activity when it's validity changes
        sigid = activity.connect("validity-changed", self._activity_validity_changed_cb)
        self._activity_sigids[actid] = sigid
        if activity.props.valid:
            self.JoinedActivity(activity.object_path())

    def remove_activity(self, activity):
        """Remove the activity from the Buddy's set of activities
        
        activity -- activity.Activity instance
        
        calls LeftActivity
        """
        actid = activity.props.id
        if not self._activities.has_key(actid):
            return
        activity.disconnect(self._activity_sigids[actid])
        del self._activity_sigids[actid]
        del self._activities[actid]
        if activity.props.valid:
            self.LeftActivity(activity.object_path())

    def get_joined_activities(self):
        """Retrieves list of still-valid activity objects"""
        acts = []
        for act in self._activities.values():
            acts.append(act)
        return acts

    def set_properties(self, properties):
        """Set the given set of properties on the object 
        
        properties -- set of property values to set 
        
        if no change, no events generated 
        if change, generates property-changed and 
            calls _update_validity
        """
        changed = False
        changed_props = {}
        if _PROP_NICK in properties.keys():
            nick = properties[_PROP_NICK]
            if nick != self._nick:
                self._nick = nick
                changed_props[_PROP_NICK] = nick
                changed = True
        if _PROP_COLOR in properties.keys():
            color = properties[_PROP_COLOR]
            if color != self._color:
                self._color = color
                changed_props[_PROP_COLOR] = color
                changed = True
        if _PROP_CURACT in properties.keys():
            curact = properties[_PROP_CURACT]
            if curact != self._current_activity:
                self._current_activity = curact
                changed_props[_PROP_CURACT] = curact
                changed = True
        if _PROP_IP4_ADDRESS in properties.keys():
            ip4addr = properties[_PROP_IP4_ADDRESS]
            if ip4addr != self._ip4_address:
                self._ip4_address = ip4addr
                changed_props[_PROP_IP4_ADDRESS] = ip4addr
                changed = True

        if not changed or not len(changed_props.keys()):
            return

        # Try emitting PropertyChanged before updating validity
        # to avoid leaking a PropertyChanged signal before the buddy is
        # actually valid the first time after creation
        if self._valid:
            dbus_changed = {}
            for key, value in changed_props.items():
                if value:
                    dbus_changed[key] = value
                else:
                    dbus_changed[key] = ""
            self.PropertyChanged(dbus_changed)

            self.emit('property-changed', changed_props)

        self._update_validity()

    def _update_validity(self):
        """Check whether we are now valid
        
        validity is True if color, nick and key are non-null
        
        emits validity-changed if we have changed validity
        """
        try:
            old_valid = self._valid
            if self._color and self._nick and self._key:
                self._valid = True
            else:
                self._valid = False

            if old_valid != self._valid:
                self.emit("validity-changed", self._valid)
        except AttributeError:
            self._valid = False

class GenericOwner(Buddy):
    """Common functionality for Local User-like objects 
    
    The TestOwner wants to produce something *like* a 
    ShellOwner, but with randomised changes and the like.
    This class provides the common features for a real 
    local owner and a testing one.
    """
    __gtype_name__ = "GenericOwner"

    __gproperties__ = {
        'registered' : (bool, None, None, False, gobject.PARAM_READWRITE | gobject.PARAM_CONSTRUCT),
        'server'     : (str, None, None, None, gobject.PARAM_READABLE | gobject.PARAM_CONSTRUCT),
        'key-hash'   : (str, None, None, None, gobject.PARAM_READABLE | gobject.PARAM_CONSTRUCT)
    }

    def __init__(self, ps, bus_name, object_id, **kwargs):
        """Initialize the GenericOwner instance 
        
        ps -- presenceservice.PresenceService object
        bus_name -- DBUS object bus name (identifier)
        object_id -- the activity's unique identifier 
        kwargs -- used to initialize the object's properties
        
        calls Buddy.__init__
        """
        self._ps = ps
        self._server = 'olpc.collabora.co.uk'
        self._key_hash = None
        self._registered = False
        if kwargs.has_key("server"):
            self._server = kwargs["server"]
            del kwargs["server"]
        if kwargs.has_key("key_hash"):
            self._key_hash = kwargs["key_hash"]
            del kwargs["key_hash"]
        if kwargs.has_key("registered"):
            self._registered = kwargs["registered"]
            del kwargs["registered"]

        self._ip4_addr_monitor = psutils.IP4AddressMonitor.get_instance()
        self._ip4_addr_monitor.connect("address-changed", self._ip4_address_changed_cb)
        if self._ip4_addr_monitor.props.address:
            kwargs["ip4-address"] = self._ip4_addr_monitor.props.address
        
        Buddy.__init__(self, bus_name, object_id, **kwargs)
        self._owner = True

        self._bus = dbus.SessionBus()
        self._bus.add_signal_receiver(self._name_owner_changed_cb,
                                    signal_name="NameOwnerChanged",
                                    dbus_interface="org.freedesktop.DBus")

    def _ip4_address_changed_cb(self, monitor, address):
        """Handle IPv4 address change, set property to generate event"""
        props = {_PROP_IP4_ADDRESS: address}
        self.set_properties(props)

    def _name_owner_changed_cb(self, name, old, new):
        """Handle D-Bus services we care about appearing and disappearing."""
        self._ip4_addr_monitor.handle_name_owner_changed(name, old, new)

    def get_registered(self):
        """Retrieve whether owner has registered with presence server"""
        return self._registered

    def get_server(self):
        """Retrieve presence server (XXX url??)"""
        return self._server

    def get_key_hash(self):
        """Retrieve the user's private-key hash"""
        return self._key_hash

    def set_registered(self, registered):
        """Customisation point: handle the registration of the owner"""
        raise RuntimeError("Subclasses must implement")

class ShellOwner(GenericOwner):
    """Representation of the local-machine owner using Sugar's Shell
    
    The ShellOwner uses the Sugar Shell's dbus services to 
    register for updates about the user's profile description.
    """
    __gtype_name__ = "ShellOwner"

    _SHELL_SERVICE = "org.laptop.Shell"
    _SHELL_OWNER_INTERFACE = "org.laptop.Shell.Owner"
    _SHELL_PATH = "/org/laptop/Shell"

    def __init__(self, ps, bus_name, object_id, test=False):
        """Initialize the ShellOwner instance 
        
        ps -- presenceservice.PresenceService object
        bus_name -- DBUS object bus name (identifier)
        object_id -- the activity's unique identifier 
        test -- ignored
        
        Retrieves initial property values from the profile 
        module.  Loads the buddy icon from file as well.
            XXX note: no error handling on that
        
        calls GenericOwner.__init__
        """
        server = profile.get_server()
        key_hash = profile.get_private_key_hash()
        registered = profile.get_server_registered()
        key = profile.get_pubkey()
        nick = profile.get_nick_name()
        color = profile.get_color().to_string()

        icon_file = os.path.join(env.get_profile_path(), "buddy-icon.jpg")
        f = open(icon_file, "r")
        icon = f.read()
        f.close()

        GenericOwner.__init__(self, ps, bus_name, object_id, key=key, nick=nick,
                color=color, icon=icon, server=server, key_hash=key_hash,
                registered=registered)

        # Connect to the shell to get notifications on Owner object
        # property changes
        try:
            self._connect_to_shell()
        except dbus.DBusException:
            pass

    def set_registered(self, value):
        """Handle notification that we have been registered"""
        if value:
            profile.set_server_registered()

    def _name_owner_changed_cb(self, name, old, new):
        # chain up to superclass
        GenericOwner._name_owner_changed_cb(self, name, old, new)

        if name != self._SHELL_SERVICE:
            return
        if (old and len(old)) and (not new and not len(new)):
            # shell went away
            self._shell_owner = None
        elif (not old and not len(old)) and (new and len(new)):
            # shell started
            self._connect_to_shell()

    def _connect_to_shell(self):
        """Connect to the Sugar Shell service to watch for events 
        
        Connects the various XChanged events on the Sugar Shell 
        service to our _x_changed_cb methods.
        """
        obj = self._bus.get_object(self._SHELL_SERVICE, self._SHELL_PATH)
        self._shell_owner = dbus.Interface(obj, self._SHELL_OWNER_INTERFACE)
        self._shell_owner.connect_to_signal('IconChanged', self._icon_changed_cb)
        self._shell_owner.connect_to_signal('ColorChanged', self._color_changed_cb)
        self._shell_owner.connect_to_signal('NickChanged', self._nick_changed_cb)
        self._shell_owner.connect_to_signal('CurrentActivityChanged',
                self._cur_activity_changed_cb)

    def _icon_changed_cb(self, icon):
        """Handle icon change, set property to generate event"""
        self.props.icon = icon

    def _color_changed_cb(self, color):
        """Handle color change, set property to generate event"""
        props = {_PROP_COLOR: color}
        self.set_properties(props)

    def _nick_changed_cb(self, nick):
        """Handle nickname change, set property to generate event"""
        props = {_PROP_NICK: nick}
        self.set_properties(props)

    def _cur_activity_changed_cb(self, activity_id):
        """Handle current-activity change, set property to generate event
        
        Filters out local activities (those not in self.activites)
        because the network users can't join those activities, so 
        the activity_id shared will be None in those cases...
        """
        if not self._activities.has_key(activity_id):
            # This activity is local-only
            activity_id = None
        props = {_PROP_CURACT: activity_id}
        self.set_properties(props)


class TestOwner(GenericOwner):
    """Class representing the owner of the machine.  This test owner
    changes random attributes periodically."""

    __gtype_name__ = "TestOwner"

    def __init__(self, ps, bus_name, object_id, test_num, randomize):
        self._cp = ConfigParser()
        self._section = "Info"
        self._test_activities = []
        self._test_cur_act = ""
        self._change_timeout = 0

        self._cfg_file = os.path.join(env.get_profile_path(), 'test-buddy-%d' % test_num)

        (pubkey, privkey, registered) = self._load_config()
        if not pubkey or not len(pubkey) or not privkey or not len(privkey):
            (pubkey, privkey) = _get_new_keypair(test_num)

        if not pubkey or not privkey:
            raise RuntimeError("Couldn't get or create test buddy keypair")

        self._save_config(pubkey, privkey, registered)
        privkey_hash = util.printable_hash(util._sha_data(privkey))

        nick = _get_random_name()
        from sugar.graphics import xocolor
        color = xocolor.XoColor().to_string()
        icon = _get_random_image()

        _logger.debug("pubkey is %s" % pubkey)
        GenericOwner.__init__(self, ps, bus_name, object_id, key=pubkey, nick=nick,
                color=color, icon=icon, registered=registered, key_hash=privkey_hash)

        # Only do the random stuff if randomize is true
        if randomize:
            self._ps.connect('connection-status', self._ps_connection_status_cb)

    def _share_reply_cb(self, actid, object_path):
        activity = self._ps.internal_get_activity(actid)
        if not activity or not object_path:
            _logger.debug("Couldn't find activity %s even though it was shared." % actid)
            return
        _logger.debug("Shared activity %s (%s)." % (actid, activity.props.name))
        self._test_activities.append(activity)

    def _share_error_cb(self, actid, err):
        _logger.debug("Error sharing activity %s: %s" % (actid, str(err)))

    def _ps_connection_status_cb(self, ps, connected):
        if not connected:
            return

        if not len(self._test_activities):
            # Share some activities
            actid = util.unique_id("Activity 1")
            callbacks = (lambda *args: self._share_reply_cb(actid, *args),
                         lambda *args: self._share_error_cb(actid, *args))
            atype = "org.laptop.WebActivity"
            properties = {"foo": "bar"}
            self._ps._share_activity(actid, atype, "Wembley Stadium", properties, callbacks)

            actid2 = util.unique_id("Activity 2")
            callbacks = (lambda *args: self._share_reply_cb(actid2, *args),
                         lambda *args: self._share_error_cb(actid2, *args))
            atype = "org.laptop.WebActivity"
            properties = {"baz": "bar"}
            self._ps._share_activity(actid2, atype, "Maine Road", properties, callbacks)

        # Change a random property ever 10 seconds
        if self._change_timeout == 0:
            self._change_timeout = gobject.timeout_add(10000, self._update_something)

    def set_registered(self, value):
        if value:
            self._registered = True

    def _load_config(self):
        if not os.path.exists(self._cfg_file):
            return (None, None, False)
        if not self._cp.read([self._cfg_file]):
            return (None, None, False)
        if not self._cp.has_section(self._section):
            return (None, None, False)

        try:
            pubkey = self._cp.get(self._section, "pubkey")
            privkey = self._cp.get(self._section, "privkey")
            registered = self._cp.get(self._section, "registered")
            return (pubkey, privkey, registered)
        except NoOptionError:
            pass

        return (None, None, False)

    def _save_config(self, pubkey, privkey, registered):
        # Save config again
        if not self._cp.has_section(self._section):
            self._cp.add_section(self._section)
        self._cp.set(self._section, "pubkey", pubkey)
        self._cp.set(self._section, "privkey", privkey)
        self._cp.set(self._section, "registered", registered)
        f = open(self._cfg_file, 'w')
        self._cp.write(f)
        f.close()

    def _update_something(self):
        it = random.randint(0, 10000) % 4
        if it == 0:
            self.props.icon = _get_random_image()
        elif it == 1:
            from sugar.graphics import xocolor
            props = {_PROP_COLOR: xocolor.XoColor().to_string()}
            self.set_properties(props)
        elif it == 2:
            props = {_PROP_NICK: _get_random_name()}
            self.set_properties(props)
        elif it == 3:
            actid = ""
            idx = random.randint(0, len(self._test_activities))
            # if idx == len(self._test_activites), it means no current
            # activity
            if idx < len(self._test_activities):
                activity = self._test_activities[idx]
                actid = activity.props.id
            props = {_PROP_CURACT: actid}
            self.set_properties(props)
        return True


def _hash_private_key(self):
    """Unused method to has a private key, see profile"""
    self.privkey_hash = None
    
    key_path = os.path.join(env.get_profile_path(), 'owner.key')
    try:
        f = open(key_path, "r")
        lines = f.readlines()
        f.close()
    except IOError, e:
        _logger.error("Error reading private key: %s" % e)
        return

    key = ""
    for l in lines:
        l = l.strip()
        if l.startswith("-----BEGIN DSA PRIVATE KEY-----"):
            continue
        if l.startswith("-----END DSA PRIVATE KEY-----"):
            continue
        key += l
    if not len(key):
        _logger.error("Error parsing public key.")

    # hash it
    key_hash = util._sha_data(key)
    self.privkey_hash = util.printable_hash(key_hash)

def _extract_public_key(keyfile):
    try:
        f = open(keyfile, "r")
        lines = f.readlines()
        f.close()
    except IOError, e:
        _logger.error("Error reading public key: %s" % e)
        return None

    # Extract the public key
    magic = "ssh-dss "
    key = ""
    for l in lines:
        l = l.strip()
        if not l.startswith(magic):
            continue
        key = l[len(magic):]
        break
    if not len(key):
        _logger.error("Error parsing public key.")
        return None
    return key

def _extract_private_key(keyfile):
    """Get a private key from a private key file"""
    # Extract the private key
    try:
        f = open(keyfile, "r")
        lines = f.readlines()
        f.close()
    except IOError, e:
        _logger.error("Error reading private key: %s" % e)
        return None

    key = ""
    for l in lines:
        l = l.strip()
        if l.startswith("-----BEGIN DSA PRIVATE KEY-----"):
            continue
        if l.startswith("-----END DSA PRIVATE KEY-----"):
            continue
        key += l
    if not len(key):
        _logger.error("Error parsing private key.")
        return None
    return key

def _get_new_keypair(num):
    """Retrieve a public/private key pair for testing"""
    # Generate keypair
    privkeyfile = os.path.join("/tmp", "test%d.key" % num)
    pubkeyfile = os.path.join("/tmp", 'test%d.key.pub' % num)

    # force-remove key files if they exist to ssh-keygen doesn't
    # start asking questions
    try:
        os.remove(pubkeyfile)
        os.remove(privkeyfile)
    except OSError:
        pass

    cmd = "ssh-keygen -q -t dsa -f %s -C '' -N ''" % privkeyfile
    import commands
    print "Generating new keypair..."
    (s, o) = commands.getstatusoutput(cmd)
    print "Done."
    pubkey = privkey = None
    if s != 0:
        _logger.error("Could not generate key pair: %d (%s)" % (s, o))
    else:
        pubkey = _extract_public_key(pubkeyfile)
        privkey = _extract_private_key(privkeyfile)

    try:
        os.remove(pubkeyfile)
        os.remove(privkeyfile)
    except OSError:
        pass
    return (pubkey, privkey)

def _get_random_name():
    """Produce random names for testing"""
    names = ["Liam", "Noel", "Guigsy", "Whitey", "Bonehead"]
    return names[random.randint(0, len(names) - 1)]

def _get_random_image():
    """Produce a random image for display"""
    import cairo, math, random, gtk

    def rand():
        return random.random()

    SIZE = 200

    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    cr = cairo.Context(s)

    # background gradient
    cr.save()
    g = cairo.LinearGradient(0, 0, 1, 1)
    g.add_color_stop_rgba(1, rand(), rand(), rand(), rand())
    g.add_color_stop_rgba(0, rand(), rand(), rand(), rand())
    cr.set_source(g)
    cr.rectangle(0, 0, SIZE, SIZE);
    cr.fill()
    cr.restore()

    # random path
    cr.set_line_width(10 * rand() + 5)
    cr.move_to(SIZE * rand(), SIZE * rand())
    cr.line_to(SIZE * rand(), SIZE * rand())
    cr.rel_line_to(SIZE * rand() * -1, 0)
    cr.close_path()
    cr.stroke()

    # a circle
    cr.set_source_rgba(rand(), rand(), rand(), rand())
    cr.arc(SIZE * rand(), SIZE * rand(), 100 * rand() + 30, 0, 2 * math.pi)
    cr.fill()

    # another circle
    cr.set_source_rgba(rand(), rand(), rand(), rand())
    cr.arc(SIZE * rand(), SIZE * rand(), 100 * rand() + 30, 0, 2 * math.pi)
    cr.fill()

    def img_convert_func(buf, data):
        data[0] += buf
        return True

    data = [""]
    pixbuf = gtk.gdk.pixbuf_new_from_data(s.get_data(), gtk.gdk.COLORSPACE_RGB,
            True, 8, s.get_width(), s.get_height(), s.get_stride())
    pixbuf.save_to_callback(img_convert_func, "jpeg", {"quality": "90"}, data)
    del pixbuf

    return str(data[0])

