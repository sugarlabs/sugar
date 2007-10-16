# Copyright (C) 2007, One Laptop Per Child
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
import time
from datetime import datetime
import os

import gobject

from sugar.datastore import dbus_helpers
from sugar import activity
from sugar.activity.activityhandle import ActivityHandle
from sugar.bundle.contentbundle import ContentBundle
from sugar.bundle.activitybundle import ActivityBundle
from sugar.bundle.contentbundle import ContentBundle
from sugar import mime

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
        
        default_keys = ['activity', 'activity_id',
                        'mime_type', 'title_set_by_user']
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

    def __contains__(self, key):
        return self._props.__contains__(key)
    
    def has_key(self, key):
        return self._props.has_key(key)

    def keys(self):
        return self._props.keys()
    
    def get_dictionary(self):
        return self._props

    def copy(self):
        return DSMetadata(self._props.copy())

    def get(self, key, default=None):
        if self._props.has_key(key):
            return self._props[key]
        else:
            return default

class DSObject(object):
    def __init__(self, object_id, metadata=None, file_path=None):
        self.object_id = object_id
        self._metadata = metadata
        self._file_path = file_path
        self._destroyed = False
        self._owns_file = False

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
            self._owns_file = True
        return self._file_path
    
    def set_file_path(self, file_path):
        if self._file_path != file_path:
            if self._file_path and self._owns_file:
                if os.path.isfile(self._file_path):
                    os.remove(self._file_path)
                self._owns_file = False
            self._file_path = file_path

    file_path = property(get_file_path, set_file_path)

    def _get_activities_for_mime(self, mime_type):
        registry = activity.get_registry()
        result = registry.get_activities_for_type(mime_type)
        if not result:
            for parent_mime in mime.get_mime_parents(mime_type):
                 result.extend(registry.get_activities_for_type(parent_type))
        return result

    def get_activities(self):
        activities = []

        bundle_id = self.metadata.get('activity', '')
        if bundle_id:
            activity_info = activity.get_registry().get_activity(bundle_id)
            if activity_info:
                activities.append(activity_info)

        mime_type = self.metadata.get('mime_type', '')
        if mime_type:
            activities_info = self._get_activities_for_mime(mime_type)
            for activity_info in activities_info:
                if activity_info.bundle_id != bundle_id:
                    activities.append(activity_info)

        return activities

    def is_activity_bundle(self):
        return self.metadata['mime_type'] in \
               [ActivityBundle.MIME_TYPE, ActivityBundle.DEPRECATED_MIME_TYPE]

    def is_content_bundle(self):
        return self.metadata['mime_type'] == ContentBundle.MIME_TYPE

    def is_bundle(self):
        return self.is_activity_bundle() or self.is_content_bundle()

    def resume(self, bundle_id=None):
        from sugar.activity import activityfactory

        if self.is_activity_bundle():
            if bundle_id is not None:
                raise ValueError('Object is a bundle, cannot be resumed as an activity.')

            bundle = ActivityBundle(self.file_path)
            if not bundle.is_installed():
                bundle.install()

            activityfactory.create(bundle.get_bundle_id())
        else:
            if not self.get_activities() and bundle_id is None:
                logging.warning('No activity can open this object.')
                return
            if bundle_id is None:
                bundle_id = self.get_activities()[0].bundle_id

            activity_id = self.metadata['activity_id']
            object_id = self.object_id

            if activity_id:
                handle = ActivityHandle(object_id=object_id,
                                        activity_id=activity_id)
                activityfactory.create(bundle_id, handle)
            else:
                activityfactory.create_with_object_id(bundle_id, object_id)

    def destroy(self):
        if self._destroyed:
            logging.warning('This DSObject has already been destroyed!.')
            import traceback;traceback.print_stack()
            return
        self._destroyed = True
        if self._file_path and self._owns_file:
            if os.path.isfile(self._file_path):
                os.remove(self._file_path)
            self._owns_file = False
        self._file_path = None

    def __del__(self):
        if not self._destroyed:
            logging.warning('DSObject was deleted without cleaning up first. ' \
                            'Please call DSObject.destroy() before disposing it.')
            self.destroy()

    def copy(self):
        return DSObject(None, self._metadata.copy(), self._file_path)

def get(object_id):
    logging.debug('datastore.get')
    metadata = dbus_helpers.get_properties(object_id)

    ds_object = DSObject(object_id, DSMetadata(metadata), None)
    # TODO: register the object for updates
    return ds_object

def create():
    metadata = DSMetadata()
    metadata['mtime'] = datetime.now().isoformat()
    metadata['timestamp'] = int(time.time())
    return DSObject(object_id=None, metadata=metadata, file_path=None)

def write(ds_object, update_mtime=True, transfer_ownership=False, reply_handler=None, error_handler=None, timeout=-1):
    logging.debug('datastore.write')

    properties = ds_object.metadata.get_dictionary().copy()

    if update_mtime:
        properties['mtime'] = datetime.now().isoformat()
        properties['timestamp'] = int(time.time())

    if ds_object._file_path is None:
        file_path = ''
    else:
        file_path = ds_object._file_path

    # FIXME: this func will be sync for creates regardless of the handlers
    # supplied. This is very bad API, need to decide what to do here.
    if ds_object.object_id:
        dbus_helpers.update(ds_object.object_id,
                            properties,
                            file_path,
                            transfer_ownership,
                            reply_handler=reply_handler,
                            error_handler=error_handler,
                            timeout=timeout)
    else:
        if reply_handler or error_handler:
            logging.warning('datastore.write() cannot currently be called async' \
                            ' for creates, see https://dev.laptop.org/ticket/3071')
        ds_object.object_id = dbus_helpers.create(properties,
                                                  file_path,
                                                  transfer_ownership)
        # TODO: register the object for updates
    logging.debug('Written object %s to the datastore.' % ds_object.object_id)

def delete(object_id):
    logging.debug('datastore.delete')
    dbus_helpers.delete(object_id)

def find(query, sorting=None, limit=None, offset=None, properties=[],
         reply_handler=None, error_handler=None):

    query = query.copy()

    if sorting:
        query['order_by'] = sorting
    if limit:
        query['limit'] = limit
    if offset:
        query['offset'] = offset
    
    props_list, total_count = dbus_helpers.find(query, properties, reply_handler, error_handler)
    
    objects = []
    for props in props_list:
        object_id = props['uid']
        del props['uid']

        ds_object = DSObject(object_id, DSMetadata(props), None)
        objects.append(ds_object)

    return objects, total_count

def copy(jobject, mount_point):

    new_jobject = jobject.copy()
    new_jobject.metadata['mountpoint'] = mount_point

    if jobject.metadata.has_key('title'):
        filename = jobject.metadata['title']

        if jobject.metadata.has_key('mime_type'):
            mime_type = jobject.metadata['mime_type']
            extension = mime.get_primary_extension(mime_type)
            if extension:
                filename += '.' + extension

        new_jobject.metadata['suggested_filename'] = filename

    # this will cause the file be retrieved from the DS
    new_jobject.file_path = jobject.file_path

    write(new_jobject)

def mount(uri, options, timeout=-1):
    return dbus_helpers.mount(uri, options, timeout=timeout)

def unmount(mount_point_id):
    dbus_helpers.unmount(mount_point_id)

def mounts():
    return dbus_helpers.mounts()

def complete_indexing():
    return dbus_helpers.complete_indexing()

def get_unique_values(key):
    return dbus_helpers.get_unique_values(key)
