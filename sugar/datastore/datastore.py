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
                    ([gobject.TYPE_PYOBJECT]))
    }

    def __init__(self, object_id, metadata, file_path):
        gobject.GObject.__init__(self)
        self.object_id = object_id
        self.metadata = metadata
        self.file_path = file_path

    def __getitem__(self, key):
        return self.metadata[key]

    def __setitem__(self, key, value):
        self.metadata[key] = value

def get(object_id):
    logging.debug('datastore.get')
    metadata = dbus_helpers.get_properties(object_id)
    file_path = dbus_helpers.get_filename(object_id)
    logging.debug('filepath: ' + file_path)
    ds_object = DSObject(object_id, metadata, file_path)
    # TODO: register the object for updates
    return ds_object

def create():
    return DSObject(object_id=None, metadata={}, file_path=None)

def write(ds_object):
    logging.debug('datastore.write')
    if ds_object.object_id:
        dbus_helpers.update(ds_object.object_id,
                            ds_object.metadata,
                            ds_object.file_path)
    else:
        ds_object.object_id = dbus_helpers.create(ds_object.metadata,
                                                  ds_object.file_path)
        # TODO: register the object for updates
    logging.debug('Written object %s to the datastore.' % ds_object.object_id)

def find(query):
    object_ids = dbus_helpers.find({})
    objects = []
    for object_id in object_ids:
        objects.append(get(object_id))
    return objects
