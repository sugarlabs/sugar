# Copyright (C) 2007-2008, One Laptop Per Child
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
import os
from datetime import datetime
import time

import dbus
import gconf

from sugar import dispatch
from sugar import mime

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

# Properties the journal cares about.
PROPERTIES = ['uid', 'title', 'mtime', 'timestamp', 'keep', 'buddies',
              'icon-color', 'mime_type', 'progress', 'activity', 'mountpoint',
              'activity_id']

class _Cache(object):

    __gtype_name__ = 'model_Cache'

    def __init__(self, entries=None):
        self._array = []
        self._dict = {}
        if entries is not None:
            self.append_all(entries)

    def prepend_all(self, entries):
        for entry in entries[::-1]:
            self._array.insert(0, entry)
            self._dict[entry['uid']] = entry

    def append_all(self, entries):
        for entry in entries:
            self._array.append(entry)
            self._dict[entry['uid']] = entry
    
    def remove_all(self, entries):
        entries = entries[:]
        for entry in entries:
            obj = self._dict[entry['uid']]
            self._array.remove(obj)
            del self._dict[entry['uid']]

    def __len__(self):
        return len(self._array)

    def __getitem__(self, key):
        if isinstance(key, basestring):
            return self._dict[key]
        else:
            return self._array[key]

class ResultSet(object):
    """Encapsulates the result of a query
    """

    _CACHE_LIMIT = 80

    def __init__(self, query):
        self._total_count  = -1
        self._position = -1
        self._query = query

        self._offset = 0
        self._cache = _Cache()

    def get_length(self):
        if self._total_count == -1:
            query = self._query.copy()
            query['limit'] = ResultSet._CACHE_LIMIT
            entries, self._total_count = self._find(query)
            self._cache.append_all(entries)
            self._offset = 0
        return self._total_count

    length = property(get_length)

    def _find(self, query):
        mount_points = query.get('mountpoints', ['/'])
        if mount_points is None or len(mount_points) != 1:
            raise ValueError('Exactly one mount point must be specified')
        if mount_points[0] == '/':
            return _get_datastore().find(query, PROPERTIES, byte_arrays=True)
        else:
            return _query_mount_point(mount_points[0], query)

    def seek(self, position):
        self._position = position

    def read(self, max_count):
        logging.debug('ResultSet.read position: %r' % self._position)

        if max_count * 5 > ResultSet._CACHE_LIMIT:
            raise RuntimeError(
                    'max_count (%i) too big for ResultSet._CACHE_LIMIT'
                    ' (%i).' % (max_count, ResultSet._CACHE_LIMIT))

        if self._position == -1:
            self.seek(0)

        if self._position < self._offset:
            remaining_forward_entries = 0
        else:
            remaining_forward_entries = self._offset + len(self._cache) - \
                                        self._position

        if self._position > self._offset + len(self._cache):
            remaining_backwards_entries = 0
        else:
            remaining_backwards_entries = self._position - self._offset

        last_cached_entry = self._offset + len(self._cache)

        if (remaining_forward_entries <= 0 and
                    remaining_backwards_entries <= 0) or \
                max_count > ResultSet._CACHE_LIMIT:

            # Total cache miss: remake it
            offset = max(0, self._position - max_count)
            logging.debug('remaking cache, offset: %r limit: %r' % \
                          (offset, max_count * 2))
            query = self._query.copy()
            query['limit'] = ResultSet._CACHE_LIMIT
            query['offset'] = offset
            entries, self._total_count = self._find(query)

            self._cache.remove_all(self._cache)
            self._cache.append_all(entries)
            self._offset = offset
            
        elif remaining_forward_entries < 2 * max_count and \
             last_cached_entry < self._total_count:

            # Add one page to the end of cache
            logging.debug('appending one more page, offset: %r' % \
                          last_cached_entry)
            query = self._query.copy()
            query['limit'] = max_count
            query['offset'] = last_cached_entry
            entries, self._total_count = self._find(query)

            # update cache
            self._cache.append_all(entries)

            # apply the cache limit
            objects_excess = len(self._cache) - ResultSet._CACHE_LIMIT
            if objects_excess > 0:
                self._offset += objects_excess
                self._cache.remove_all(self._cache[:objects_excess])

        elif remaining_backwards_entries < 2 * max_count and self._offset > 0:

            # Add one page to the beginning of cache
            limit = min(self._offset, max_count)
            self._offset = max(0, self._offset - max_count)

            logging.debug('prepending one more page, offset: %r limit: %r' % 
                          (self._offset, limit))
            query = self._query.copy()
            query['limit'] = limit
            query['offset'] = self._offset
            entries, self._total_count = self._find(query)

            # update cache
            self._cache.prepend_all(entries)

            # apply the cache limit
            objects_excess = len(self._cache) - ResultSet._CACHE_LIMIT
            if objects_excess > 0:
                self._cache.remove_all(self._cache[-objects_excess:])
        else:
            logging.debug('cache hit and no need to grow the cache')

        first_pos = self._position - self._offset
        last_pos = self._position - self._offset + max_count
        return self._cache[first_pos:last_pos]

def _get_file_metadata(path):
    stat = os.stat(path)
    client = gconf.client_get_default()
    return {'uid': path,
            'title': os.path.basename(path),
            'timestamp': stat.st_mtime,
            'mime_type': mime.get_for_file(path),
            'activity': '',
            'activity_id': '',
            'icon-color': client.get_string('/desktop/sugar/user/color')}

def _get_all_files(dir_path):
    files = []
    for entry in os.listdir(dir_path):
        full_path = os.path.join(dir_path, entry)
        if os.path.isdir(full_path):
            files.extend(_get_all_files(full_path))
        elif os.path.isfile(full_path):
            stat = os.stat(full_path)
            files.append((full_path, stat.st_mtime))
    return files

def _query_mount_point(mount_point, query):
    t = time.time()

    files = _get_all_files(mount_point)
    offset = int(query.get('offset', 0))
    limit  = int(query.get('limit', len(files)))

    total_count = len(files)
    files.sort(lambda a, b: int(b[1] - a[1]))
    files = files[offset:offset + limit]

    result = []
    for file_path, timestamp in files:
        metadata = _get_file_metadata(file_path)
        metadata['mountpoint'] = mount_point
        result.append(metadata)

    logging.debug('_query_mount_point took %f s.' % (time.time() - t))

    return result, total_count

_datastore = None
def _get_datastore():
    global _datastore
    if _datastore is None:
        bus = dbus.SessionBus()
        remote_object = bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH)
        _datastore = dbus.Interface(remote_object, DS_DBUS_INTERFACE)

    return _datastore

def find(query):
    """Returns a ResultSet
    """
    if 'order_by' not in query:
        query['order_by'] = ['-mtime']
    return ResultSet(query)

def _get_mount_point(path):
    dir_path = os.path.dirname(path)
    while True:
        if os.path.ismount(dir_path):
            return dir_path
        else:
            dir_path = dir_path.rsplit(os.sep, 1)[0]

def get(object_id):
    """Returns the metadata for an object
    """
    if os.path.exists(object_id):
        metadata = _get_file_metadata(object_id)
        metadata['mountpoint'] = _get_mount_point(object_id)
    else:
        metadata = _get_datastore().get_properties(object_id, byte_arrays=True)
        metadata['mountpoint'] = '/'
    return metadata

def get_file(object_id):
    """Returns the file for an object
    """
    if os.path.exists(object_id):
        return object_id
    else:
        return _get_datastore().get_filename(object_id)

def get_unique_values(key):
    """Returns a list with the different values a property has taken
    """
    empty_dict = dbus.Dictionary({}, signature='ss')
    return _get_datastore().get_uniquevaluesfor(key, empty_dict)

def delete(object_id):
    """Removes an object from persistent storage
    """
    if os.path.exists(object_id):
        os.unlink(object_id)
    else:
        _get_datastore().delete(object_id)

def copy(metadata, mount_point):
    """Copies an object to another mount point
    """
    metadata = get(metadata['uid'])

    #TODO: figure out the best place to get rid of that temp file
    file_path = get_file(metadata['uid'])

    metadata['mountpoint'] = mount_point
    del metadata['uid']

    return write(metadata, file_path)

def write(metadata, file_path='', update_mtime=True):
    """Creates or updates an entry for that id
    """
    if update_mtime:
        metadata['mtime'] = datetime.now().isoformat()
        metadata['timestamp'] = int(time.time())

    if metadata['mountpoint'] == '/':
        if metadata.get('uid', ''):
            object_id = _get_datastore().update(metadata['uid'],
                                                 dbus.Dictionary(metadata),
                                                 file_path,
                                                 True)
        else:
            object_id = _get_datastore().create(dbus.Dictionary(metadata),
                                                 file_path,
                                                 True)
    else:
        pass

    return object_id

created = dispatch.Signal()
updated = dispatch.Signal()
deleted = dispatch.Signal()

