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

def _bytes_to_string(bytes):
    if len(bytes):
        return ''.join([chr(item) for item in bytes])
    return None


class Buddy(gobject.GObject):

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
        'icon'             : (object, None, None, gobject.PARAM_READABLE),
        'nick'             : (str, None, None, None, gobject.PARAM_READABLE),
        'color'            : (str, None, None, None, gobject.PARAM_READABLE),
        'current-activity' : (str, None, None, None, gobject.PARAM_READABLE),
        'owner'            : (bool, None, None, False, gobject.PARAM_READABLE)
    }

    _PRESENCE_SERVICE = "org.laptop.Sugar.Presence"
    _BUDDY_DBUS_INTERFACE = "org.laptop.Sugar.Presence.Buddy"

    def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
        gobject.GObject.__init__(self)
        self._object_path = object_path
        self._ps_new_object = new_obj_cb
        self._ps_del_object = del_obj_cb
        self._properties = {}
        bobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
        self._buddy = dbus.Interface(bobj, self._BUDDY_DBUS_INTERFACE)
        self._buddy.connect_to_signal('IconChanged', self._icon_changed_cb)
        self._buddy.connect_to_signal('JoinedActivity', self._joined_activity_cb)
        self._buddy.connect_to_signal('LeftActivity', self._left_activity_cb)
        self._buddy.connect_to_signal('PropertyChanged', self._property_changed_cb)
        self._properties = self._get_properties_helper()

        self._activities = {}
        self._icon = None

    def _get_properties_helper(self):
        props = self._buddy.GetProperties()
        if not props:
            return {}
        return props

    def do_get_property(self, pspec):
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
            if not self._activities.has_key(curact):
                return None
            return self._activities[curact]
        elif pspec.name == "owner":
            return self._properties["owner"]
        elif pspec.name == "icon":
            if not self._icon:
                self._icon = _bytes_to_string(self._buddy.GetIcon())
            return self._icon

    def object_path(self):
        return self._object_path

    def _emit_icon_changed_signal(self, bytes):
        self._icon = _bytes_to_string(bytes)
        self.emit('icon-changed')
        return False

    def _icon_changed_cb(self, icon_data):
        gobject.idle_add(self._emit_icon_changed_signal, icon_data)

    def _emit_joined_activity_signal(self, object_path):
        self.emit('joined-activity', self._ps_new_object(object_path))
        return False

    def _joined_activity_cb(self, object_path):
        if not self._activities.has_key(object_path):
            self._activities[object_path] = self._ps_new_object(object_path)
        gobject.idle_add(self._emit_joined_activity_signal, object_path)

    def _emit_left_activity_signal(self, object_path):
        self.emit('left-activity', self._ps_new_object(object_path))
        return False

    def _left_activity_cb(self, object_path):
        if self._activities.has_key(object_path):
            del self._activities[object_path]
        gobject.idle_add(self._emit_left_activity_signal, object_path)

    def _handle_property_changed_signal(self, prop_list):
        self._properties = self._get_properties_helper()
        # FIXME: don't leak unexposed property names
        self.emit('property-changed', prop_list)
        return False

    def _property_changed_cb(self, prop_list):
        gobject.idle_add(self._handle_property_changed_signal, prop_list)

    def get_icon_pixbuf(self):
        if self.props.icon and len(self.props.icon):
            pbl = gtk.gdk.PixbufLoader()
            icon_data = ""
            for item in self.props.icon:
                icon_data = icon_data + chr(item)
            pbl.write(icon_data)
            pbl.close()
            return pbl.get_pixbuf()
        else:
            return None

    def get_joined_activities(self):
        try:
            resp = self._buddy.GetJoinedActivities()
        except dbus.exceptions.DBusException:
            return []
        acts = []
        for item in resp:
            acts.append(self._ps_new_object(item))
        return acts
