"""UI interface to a buddy in the presence service"""
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

import gobject
import gtk
import dbus


class Buddy(gobject.GObject):
    """UI interface for a Buddy in the presence service
    
    Each buddy interface tracks a set of activities and properties
    that can be queried to provide UI controls for manipulating 
    the presence interface.
    
    Properties Dictionary:
        'key': public key, 
        'nick': nickname , 
        'color': color (XXX what format), 
        'current-activity': (XXX dbus path?), 
        'owner': (XXX dbus path?), 
        'icon': (XXX pixel data for an icon?)
    See __gproperties__
    """
    __gsignals__ = {
        'icon-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([])),
        'joined-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'left-activity': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
        'property-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([gobject.TYPE_PYOBJECT])),
    }

    __gproperties__ = {
        'key'              : (str, None, None, None, gobject.PARAM_READABLE),
        'icon'             : (str, None, None, None, gobject.PARAM_READABLE),
        'nick'             : (str, None, None, None, gobject.PARAM_READABLE),
        'color'            : (str, None, None, None, gobject.PARAM_READABLE),
        'current-activity' : (object, None, None, gobject.PARAM_READABLE),
        'owner'            : (bool, None, None, False, gobject.PARAM_READABLE),
        'ip4-address'      : (str, None, None, None, gobject.PARAM_READABLE)
    }

    _PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
    _BUDDY_DBUS_INTERFACE = "org.laptop.Sugar.Presence.Buddy"

    def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
        """Initialise the reference to the buddy
        
        bus -- dbus bus object 
        new_obj_cb -- callback to call when this buddy joins an activity 
        del_obj_cb -- callback to call when this buddy leaves an activity 
        object_path -- path to the buddy object 
        """
        gobject.GObject.__init__(self)
        self._object_path = object_path
        self._ps_new_object = new_obj_cb
        self._ps_del_object = del_obj_cb
        self._properties = {}
        self._activities = {}

        bobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
        self._buddy = dbus.Interface(bobj, self._BUDDY_DBUS_INTERFACE)
        self._buddy.connect_to_signal('IconChanged', self._icon_changed_cb,
                                      byte_arrays=True)
        self._buddy.connect_to_signal('JoinedActivity', self._joined_activity_cb)
        self._buddy.connect_to_signal('LeftActivity', self._left_activity_cb)
        self._buddy.connect_to_signal('PropertyChanged', self._property_changed_cb)
        self._properties = self._get_properties_helper()

        activities = self._buddy.GetJoinedActivities()
        for op in activities:
            self._activities[op] = self._ps_new_object(op)
        self._icon = None

    def _get_properties_helper(self):
        """Retrieve the Buddy's property dictionary from the service object
        """
        props = self._buddy.GetProperties(byte_arrays=True)
        if not props:
            return {}
        return props

    def do_get_property(self, pspec):
        """Retrieve a particular property from our property dictionary 
        
        pspec -- XXX some sort of GTK specifier object with attributes
            including 'name', 'active' and 'icon-name'
        """
        if pspec.name == "key":
            return self._properties["key"]
        elif pspec.name == "nick":
            return self._properties["nick"]
        elif pspec.name == "color":
            return self._properties["color"]
        elif pspec.name == "current-activity":
            if not self._properties.has_key("current-activity"):
                return None
            curact = self._properties["current-activity"]
            if not len(curact):
                return None
            for activity in self._activities.values():
                if activity.props.id == curact:
                    return activity
            return None
        elif pspec.name == "owner":
            return self._properties["owner"]
        elif pspec.name == "icon":
            if not self._icon:
                self._icon = str(self._buddy.GetIcon(byte_arrays=True))
            return self._icon
        elif pspec.name == "ip4-address":
            # IPv4 address will go away quite soon
            if not self._properties.has_key("ip4-address"):
                return None
            return self._properties["ip4-address"]

    def object_path(self):
        """Retrieve our dbus object path"""
        return self._object_path

    def _emit_icon_changed_signal(self, bytes):
        """Emit GObject signal when icon has changed"""
        self._icon = str(bytes)
        self.emit('icon-changed')
        return False

    def _icon_changed_cb(self, icon_data):
        """Handle dbus signal by emitting a GObject signal"""
        gobject.idle_add(self._emit_icon_changed_signal, icon_data)

    def _emit_joined_activity_signal(self, object_path):
        """Emit activity joined signal with Activity object"""
        self.emit('joined-activity', self._ps_new_object(object_path))
        return False

    def _joined_activity_cb(self, object_path):
        """Handle dbus signal by emitting a GObject signal
        
        Stores the activity in activities dictionary as well
        """
        if not self._activities.has_key(object_path):
            self._activities[object_path] = self._ps_new_object(object_path)
        gobject.idle_add(self._emit_joined_activity_signal, object_path)

    def _emit_left_activity_signal(self, object_path):
        """Emit activity left signal with Activity object
        
        XXX this calls self._ps_new_object instead of self._ps_del_object,
            which would seem to be the incorrect callback?
        """
        self.emit('left-activity', self._ps_new_object(object_path))
        return False

    def _left_activity_cb(self, object_path):
        """Handle dbus signal by emitting a GObject signal
        
        Also removes from the activities dictionary
        """
        if self._activities.has_key(object_path):
            del self._activities[object_path]
        gobject.idle_add(self._emit_left_activity_signal, object_path)

    def _handle_property_changed_signal(self, prop_list):
        """Emit property-changed signal with property dictionary 
        
        Generates a property-changed signal with the results of 
        _get_properties_helper()
        """
        self._properties = self._get_properties_helper()
        # FIXME: don't leak unexposed property names
        self.emit('property-changed', prop_list)
        return False

    def _property_changed_cb(self, prop_list):
        """Handle dbus signal by emitting a GObject signal"""
        gobject.idle_add(self._handle_property_changed_signal, prop_list)

    def get_icon_pixbuf(self):
        """Retrieve Buddy's icon as a GTK pixel buffer
        
        XXX Why aren't the icons coming in as SVG?
        """
        if self.props.icon and len(self.props.icon):
            pbl = gtk.gdk.PixbufLoader()
            pbl.write(self.props.icon)
            pbl.close()
            return pbl.get_pixbuf()
        else:
            return None

    def get_joined_activities(self):
        """Retrieve the set of all activities which this buddy has joined 
        
        Uses the GetJoinedActivities method on the service 
        object to produce object paths, wraps each in an 
        Activity object.  
        
        returns list of presence Activity objects
        """
        try:
            resp = self._buddy.GetJoinedActivities()
        except dbus.exceptions.DBusException:
            return []
        acts = []
        for item in resp:
            acts.append(self._ps_new_object(item))
        return acts
