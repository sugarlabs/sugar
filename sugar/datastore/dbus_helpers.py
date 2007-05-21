# Copyright (C) 2006, Red Hat, Inc.
# Copyright (C) 2007, One Laptop Per Child
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
import logging

import dbus
import dbus.glib
import gobject

from sugar import util

DS_DBUS_SERVICE = "org.laptop.sugar.DataStore"
DS_DBUS_INTERFACE = "org.laptop.sugar.DataStore"
DS_DBUS_PATH = "/org/laptop/sugar/DataStore"

_bus = dbus.SessionBus()
try:
    _data_store = dbus.Interface(_bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH),
                                 DS_DBUS_INTERFACE)
except Exception, e:
    _data_store = None
    logging.error(e)

def create(properties, filename):
    object_id = _data_store.create(dbus.Dictionary(properties), filename)
    logging.debug('dbus_helpers.create: ' + object_id)
    return object_id

def update(uid, properties, filename, reply_handler=None, error_handler=None):
    logging.debug('dbus_helpers.update: %s, %s' % (uid, filename))
    if reply_handler and error_handler:
        _data_store.update(uid, dbus.Dictionary(properties), filename,
                reply_handler=reply_handler,
                error_handler=error_handler)
    else:
        _data_store.update(uid, dbus.Dictionary(properties), filename)

def get_properties(uid):
    logging.debug('dbus_helpers.get_properties: %s' % uid)
    return _data_store.get_properties(uid)

def get_filename(uid):
    filename = _data_store.get_filename(uid)
    logging.debug('dbus_helpers.get_filename: %s, %s' % (uid, filename))
    return filename

def find(query, reply_handler, error_handler):
    logging.debug('dbus_helpers.find')
    if reply_handler and error_handler:
        return _data_store.find(query, reply_handler=reply_handler,
                error_handler=error_handler)
    else:
        return _data_store.find(query)
"""


class DataStoreObject(gobject.GObject):

    __gsignals__ = {
        'updated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                    ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, metadata, file_path=None, handle=None):
        self._metadata = metadata
        self.file_path = file_path
        self.handle = handle

    def __getitem__(self, key):
        return self._metadata[key]

    def __setitem__(self, key, value):
        self._metadata[key] = value

    def get_metadata(self):
        return self._metadata

def _read_from_object_path(object_path):
    dbus_object = _bus.get_object(DS_DBUS_SERVICE, object_path)
    metadata = dbus_object.get_properties(dbus.Dictionary({}, signature='sv'))

    object_type = metadata['object-type']
    file_path = metadata['file-path']
    handle = metadata['handle']

    del metadata['object-type']    
    del metadata['file-path']    
    del metadata['handle']

    return DataStoreObject(metadata, file_path, handle)

def create():
    return DataStoreObject({})

def read(handle):
    object_path = _data_store.get(handle)
    return _read_from_object_path(object_path)

def write(obj):
    if obj.handle:
        _data_store.update(int(obj.handle),
                           dbus.Dictionary(obj.get_metadata().copy()),
                           obj.get_file_path())
    else:
        object_path = _data_store.create(dbus.Dictionary(metadata),
                                         obj.get_file_path())
        dbus_object = _bus.get_object(DS_DBUS_SERVICE, object_path)
        obj.handle = dbus_object.get_properties(['handle'])['handle']

def find(query):
    object_paths = _data_store.find(query)
    objects = []
    for object_path in object_paths:
        objects.append(_read_from_object_path(object_path))
    return objects

def delete(handle):
    pass

################################################################################

class ObjectCache(object):
    def __init__(self):
        self._cache = {}

    def get(self, object_path):
        try:
            return self._cache[object_path]
        except KeyError:
            return None

    def add(self, obj):
        op = obj.object_path()
        if not self._cache.has_key(op):
            self._cache[op] = obj

    def remove(self, object_path):
        try:
            del self._cache[object_path]
        except IndexError:
            pass



class DSObject(gobject.GObject):

    __gsignals__ = {
        'updated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                    ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }

    _DS_OBJECT_DBUS_INTERFACE = "org.laptop.sugar.DataStore.Object"

    def __init__(self, bus, new_obj_cb, del_obj_cb, object_path):
        gobject.GObject.__init__(self)
        self._object_path = object_path
        self._ps_new_object = new_obj_cb
        self._ps_del_object = del_obj_cb
        bobj = bus.get_object(DS_DBUS_SERVICE, object_path)
        self._dsobj = dbus.Interface(bobj, self._DS_OBJECT_DBUS_INTERFACE)
        self._dsobj.connect_to_signal('Updated', self._updated_cb)
        self._data = None
        self._data_needs_update = True
        self._properties = None
        self._deleted = False

    def object_path(self):
        return self._object_path

    def uid(self):
        if not self._properties:
            self._properties = self._dsobj.get_properties([])
        return self._properties['uid']

    def _emit_updated_signal(self, data, prop_dict, deleted):
        self.emit('updated', data, prop_dict, deleted)
        return False

    def _update_internal_properties(self, prop_dict):
        did_update = False
        for (key, value) in prop_dict.items():
            if not len(value):
                if self._properties.has_key(ley):
                    did_update = True
                    del self._properties[key]
            else:
                if self._properties.has_key(key):
                    if self._properties[key] != value:
                        did_update = True
                        self._properties[key] = value
                else:
                    did_update = True
                    self._properties[key] = value
        return did_update

    def _updated_cb(self, data=False, prop_dict={}, deleted=False):
        if self._update_internal_properties(prop_dict):
            gobject.idle_add(self._emit_updated_signal, data, prop_dict, deleted)
        self._deleted = deleted

    def get_data(self):
        if self._data_needs_update:
            data = self._dsobj.get_data()
            self._data = ""
            for c in data:
                self._data += chr(c)
        return self._data

    def set_data(self, data):
        old_data = self._data
        self._data = data
        try:
            self._dsobj.set_data(dbus.ByteArray(data))
            del old_data
        except dbus.DBusException, e:
            self._data = old_data
            raise e

    def set_properties(self, prop_dict):
        old_props = self._properties
        self._update_internal_properties(prop_dict)
        try:
            self._dsobj.set_properties(prop_dict)
            del old_props
        except dbus.DBusException, e:
            self._properties = old_props
            raise e

    def get_properties(self, prop_list=[]):
        if not self._properties:
            self._properties = self._dsobj.get_properties(prop_list)
        return self._properties

class DataStore(gobject.GObject):

    _DS_DBUS_OBJECT_PATH = DS_DBUS_PATH + "/Object/"

    def __init__(self):
        gobject.GObject.__init__(self)
        self._objcache = ObjectCache()
        self._bus = dbus.SessionBus()
        self._ds = dbus.Interface(self._bus.get_object(DS_DBUS_SERVICE,
                DS_DBUS_PATH), DS_DBUS_INTERFACE)

    def _new_object(self, object_path):
        obj = self._objcache.get(object_path)
        if obj:
            return obj

        if object_path.startswith(self._DS_DBUS_OBJECT_PATH):
            obj = DSObject(self._bus, self._new_object,
                    self._del_object, object_path)
        else:
            raise RuntimeError("Unknown object type")
        self._objcache.add(obj)
        return obj

    def _del_object(self, object_path):
        # FIXME
        pass

    def get(self, uid=None, activity_id=None):
        if not activity_id and not uid:
            raise ValueError("At least one of activity_id or uid must be specified")
        if activity_id and uid:
            raise ValueError("Only one of activity_id or uid can be specified")
        if activity_id:
            if not util.validate_activity_id(activity_id):
                raise ValueError("activity_id must be valid")
            return self._new_object(self._ds.getActivityObject(activity_id))
        elif uid:
            if not len(uid):
                raise ValueError("uid must be valid")
            return self._new_object(self._ds.get(int(uid)))
        raise RuntimeError("At least one of activity_id or uid must be specified")

    def create(self, data, prop_dict={}, activity_id=None):
        if activity_id and not util.validate_activity_id(activity_id):
            raise ValueError("activity_id must be valid")
        if not activity_id:
            activity_id = ""
        op = self._ds.create(dbus.ByteArray(data), dbus.Dictionary(prop_dict), activity_id)
        return self._new_object(op)

    def delete(self, obj):
        op = obj.object_path()
        obj = self._objcache.get(op)
        if not obj:
            raise RuntimeError("Object not found.")
        self._ds.delete(op)

    def find(self, prop_dict):
        ops = self._ds.find(dbus.Dictionary(prop_dict))
        objs = []
        for op in ops:
            objs.append(self._new_object(op))
        return objs

_ds = None
def get_instance():
    global _ds
    if not _ds:
        _ds = DataStore()
    return _ds

"""
