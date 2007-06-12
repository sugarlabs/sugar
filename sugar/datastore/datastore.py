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

import gobject

from sugar.datastore import dbus_helpers

class DSMetadata(gobject.GObject):
    __gsignals__ = {
        'updated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                    ([]))
    }

    def __init__(self, props=None):
        gobject.GObject.__init__(self)
        if not props:
            self._props = {}
        else:
            self._props = props
        
        default_keys = ['activity', 'mime_type']
        for key in default_keys:
            if not self._props.has_key(key):
                self._props[key] = ''

    def __getitem__(self, key):
        return self._props[key]

    def __setitem__(self, key, value):
        if not self._props.has_key(key) or self._props[key] != value:
            self._props[key] = value
            self.emit('updated')

    def __delitem__(self, key):
        del self._props[key]

    def has_key(self, key):
        return self._props.has_key(key)
    
    def get_dictionary(self):
        return self._props

class DSObject:
    def __init__(self, object_id, metadata=None, file_path=None):
        self.object_id = object_id
        self._metadata = metadata
        self._file_path = file_path

    def get_metadata(self):
        if self._metadata is None and not self.object_id is None:
            metadata = DSMetadata(dbus_helpers.get_properties(self.object_id))
            self._metadata = metadata
        return self._metadata
    
    def set_metadata(self, metadata):
        if self._metadata != metadata:
            self._metadata = metadata

    metadata = property(get_metadata, set_metadata)

    def get_file_path(self):
        if self._file_path is None and not self.object_id is None:
            self.set_file_path(dbus_helpers.get_filename(self.object_id))
        return self._file_path
    
    def set_file_path(self, file_path):
        if self._file_path != file_path:
            self._file_path = file_path

    file_path = property(get_file_path, set_file_path)

def get(object_id):
    logging.debug('datastore.get')
    metadata = dbus_helpers.get_properties(object_id)
    file_path = dbus_helpers.get_filename(object_id)

    ds_object = DSObject(object_id, DSMetadata(metadata), file_path)
    # TODO: register the object for updates
    return ds_object

def create():
    return DSObject(object_id=None, metadata=DSMetadata(), file_path=None)

def write(ds_object, reply_handler=None, error_handler=None):
    logging.debug('datastore.write: %r' % ds_object.metadata.get_dictionary())
    if ds_object.object_id:
        dbus_helpers.update(ds_object.object_id,
                            ds_object.metadata.get_dictionary(),
                            ds_object.file_path,
                            reply_handler=reply_handler,
                            error_handler=error_handler)
    else:
        ds_object.object_id = dbus_helpers.create(ds_object.metadata.get_dictionary(),
                                                  ds_object.file_path)
        # TODO: register the object for updates
    logging.debug('Written object %s to the datastore.' % ds_object.object_id)

def find(query, sorting=None, limit=None, offset=None, reply_handler=None,
         error_handler=None):
    if sorting:
        query['order_by'] = sorting
    if limit:
        query['limit'] = limit
    if offset:
        query['offset'] = offset
    
    props_list, total_count = dbus_helpers.find(query, reply_handler, error_handler)
    
    objects = []
    for props in props_list:
        if props.has_key('filename') and props['filename']:
            file_path = props['filename']
            del props['filename']
        else:
            file_path = None

        object_id = props['uid']
        del props['uid']

        ds_object = DSObject(object_id, DSMetadata(props), file_path)
        objects.append(ds_object)

    return objects, total_count

