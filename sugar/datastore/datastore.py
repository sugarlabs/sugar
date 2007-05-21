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

class DSObject(gobject.GObject):
    __gsignals__ = {
        'updated': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                    ([]))
    }

    def __init__(self, object_id, metadata, file_path):
        gobject.GObject.__init__(self)
        self.object_id = object_id
        self._metadata = metadata
        self._file_path = file_path

    def __getitem__(self, key):
        return self.metadata[key]

    def __setitem__(self, key, value):
        if not self.metadata.has_key(key) or self.metadata[key] != value:
            self.metadata[key] = value
            self.emit('updated')

    def __delitem__(self, key):
        del self.metadata[key]

    def get_metadata(self):
        return self._metadata
    
    def set_metadata(self, metadata):
        if self._metadata != metadata:
            self._metadata = metadata
            self.emit('updated')

    metadata = property(get_metadata, set_metadata)

    def get_file_path(self):
        return self._file_path
    
    def set_file_path(self, file_path):
        if self._file_path != file_path:
            self._file_path = file_path
            self.emit('updated')

    file_path = property(get_file_path, set_file_path)

def get(object_id):
    logging.debug('datastore.get')
    metadata = dbus_helpers.get_properties(object_id)
    file_path = dbus_helpers.get_filename(object_id)

    ds_object = DSObject(object_id, metadata, file_path)
    # TODO: register the object for updates
    return ds_object

def create():
    return DSObject(object_id=None, metadata={}, file_path=None)

def write(ds_object, reply_handler=None, error_handler=None):
    logging.debug('datastore.write')
    if ds_object.object_id:
        dbus_helpers.update(ds_object.object_id,
                            ds_object.metadata,
                            ds_object.file_path,
                            reply_handler=reply_handler,
                            error_handler=error_handler)
    else:
        ds_object.object_id = dbus_helpers.create(ds_object.metadata,
                                                  ds_object.file_path)
        # TODO: register the object for updates
    logging.debug('Written object %s to the datastore.' % ds_object.object_id)

def find(query, reply_handler=None, error_handler=None):
    object_ids = dbus_helpers.find(query, reply_handler, error_handler)
    objects = []
    for object_id in object_ids:
        objects.append(get(object_id))
    return objects
