# Copyright (C) 2006, Red Hat, Inc.
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
import dbus


def _one_dict_differs(dict1, dict2):
    diff_keys = []
    for key, value in dict1.items():
        if not dict2.has_key(key) or dict2[key] != value:
            diff_keys.append(key)
    return diff_keys

def _dicts_differ(dict1, dict2):
    diff_keys = []
    diff1 = _one_dict_differs(dict1, dict2)
    diff2 = _one_dict_differs(dict2, dict1)
    for key in diff2:
        if key not in diff1:
            diff_keys.append(key)
    diff_keys += diff1
    return diff_keys

class Service(gobject.GObject):

    _PRESENCE_SERVICE = "org.laptop.Presence"
    _SERVICE_DBUS_INTERFACE = "org.laptop.Presence.Service"

    __gsignals__ = {
        'published-value-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                   ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
        gobject.GObject.__init__(self)
        self._object_path = object_path
        self._ps_new_object = new_obj_cb
        self._ps_del_object = del_obj_cb
        sobj = bus.get_object(self._PRESENCE_SERVICE, object_path)
        self._service = dbus.Interface(sobj, self._SERVICE_DBUS_INTERFACE)
        self._service.connect_to_signal('PropertyChanged', self.__property_changed_cb)
        self._service.connect_to_signal('PublishedValueChanged',
                self.__published_value_changed_cb)
        self._props = self._service.getProperties()
        self._pubvals = self._service.getPublishedValues()

    def object_path(self):
        return self._object_path

    def __property_changed_cb(self, prop_list):
        self._props = self._service.getProperties()

    def get_published_value(self, key):
        return self._pubvals[key]

    def get_published_values(self):
        self._pubvals = self._service.getPublishedValues()
        return self._pubvals

    def set_published_value(self, key, value):
        if self._pubvals.has_key(key):
            if self._pubvals[key] == value:
                return
        self._pubvals[key] = value
        self._service.setPublishedValue(key, value)

    def set_published_values(self, vals):
        self._service.setPublishedValues(vals)
        self._pubvals = vals

    def __published_value_changed_cb(self, keys):
        oldvals = self._pubvals
        self.get_published_values()
        diff_keys = _dicts_differ(oldvals, self._pubvals)
        if len(diff_keys) > 0:
            self.emit('published-value-changed', diff_keys)

    def get_name(self):
        return self._props['name']

    def get_type(self):
        return self._props['type']

    def get_domain(self):
        return self._props['domain']

    def get_address(self):
        if self._props.has_key('address'):
            return self._props['address']
        return None

    def get_activity_id(self):
        if self._props.has_key('activityId'):
            return self._props['activityId']
        return None

    def get_port(self):
        if self._props.has_key('port'):
            return self._props['port']
        return None

    def get_source_address(self):
        if self._props.has_key('sourceAddress'):
            return self._props['sourceAddress']
        return None
