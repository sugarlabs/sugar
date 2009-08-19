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
import shutil
from stat import S_IFMT, S_IFDIR, S_IFREG
import re

import gobject
import dbus
import gconf
import gio

from sugar import dispatch
from sugar import mime
from sugar import util

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

# Properties the journal cares about.
PROPERTIES = ['uid', 'title', 'mtime', 'timestamp', 'keep', 'buddies',
              'icon-color', 'mime_type', 'progress', 'activity', 'mountpoint',
              'activity_id', 'bundle_id']

MIN_PAGES_TO_CACHE = 3
MAX_PAGES_TO_CACHE = 5

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
        for uid in [entry['uid'] for entry in entries]:
            obj = self._dict[uid]
            self._array.remove(obj)
            del self._dict[uid]

    def __len__(self):
        return len(self._array)

    def __getitem__(self, key):
        if isinstance(key, basestring):
            return self._dict[key]
        else:
            return self._array[key]

class BaseResultSet(object):
    """Encapsulates the result of a query
    """

    def __init__(self, query, page_size):
        self._total_count  = -1
        self._position = -1
        self._query = query
        self._page_size = page_size

        self._offset = 0
        self._cache = _Cache()

        self.ready = dispatch.Signal()
        self.progress = dispatch.Signal()

    def setup(self):
        self.ready.send(self)

    def stop(self):
        pass

    def get_length(self):
        if self._total_count == -1:
            query = self._query.copy()
            query['limit'] = self._page_size * MIN_PAGES_TO_CACHE
            entries, self._total_count = self.find(query)
            self._cache.append_all(entries)
            self._offset = 0
        return self._total_count

    length = property(get_length)

    def find(self, query):
        raise NotImplementedError()

    def seek(self, position):
        self._position = position

    def read(self):
        logging.debug('ResultSet.read position: %r', self._position)

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

        if remaining_forward_entries <= 0 and remaining_backwards_entries <= 0:

            # Total cache miss: remake it
            limit = self._page_size * MIN_PAGES_TO_CACHE
            offset = max(0, self._position - limit / 2)
            logging.debug('remaking cache, offset: %r limit: %r', offset,
                limit)
            query = self._query.copy()
            query['limit'] = limit
            query['offset'] = offset
            entries, self._total_count = self.find(query)

            self._cache.remove_all(self._cache)
            self._cache.append_all(entries)
            self._offset = offset

        elif remaining_forward_entries <= 0 and remaining_backwards_entries > 0:

            # Add one page to the end of cache
            logging.debug('appending one more page, offset: %r',
                last_cached_entry)
            query = self._query.copy()
            query['limit'] = self._page_size
            query['offset'] = last_cached_entry
            entries, self._total_count = self.find(query)

            # update cache
            self._cache.append_all(entries)

            # apply the cache limit
            cache_limit = self._page_size * MAX_PAGES_TO_CACHE
            objects_excess = len(self._cache) - cache_limit
            if objects_excess > 0:
                self._offset += objects_excess
                self._cache.remove_all(self._cache[:objects_excess])

        elif remaining_forward_entries > 0 and \
                remaining_backwards_entries <= 0 and self._offset > 0:

            # Add one page to the beginning of cache
            limit = min(self._offset, self._page_size)
            self._offset = max(0, self._offset - limit)

            logging.debug('prepending one more page, offset: %r limit: %r',
                self._offset, limit)
            query = self._query.copy()
            query['limit'] = self._page_size
            query['offset'] = self._offset
            entries, self._total_count = self.find(query)

            # update cache
            self._cache.prepend_all(entries)

            # apply the cache limit
            cache_limit = self._page_size * MAX_PAGES_TO_CACHE
            objects_excess = len(self._cache) - cache_limit
            if objects_excess > 0:
                self._cache.remove_all(self._cache[-objects_excess:])
        else:
            logging.debug('cache hit and no need to grow the cache')

        return self._cache[self._position - self._offset]

class DatastoreResultSet(BaseResultSet):
    """Encapsulates the result of a query on the datastore
    """
    def __init__(self, query, page_size):

        if query.get('query', '') and not query['query'].startswith('"'):
            query_text = ''
            words = query['query'].split(' ')
            for word in words:
                if word:
                    if query_text:
                        query_text += ' '
                    query_text += word + '*'

            query['query'] = query_text

        BaseResultSet.__init__(self, query, page_size)

    def find(self, query):
        entries, total_count = _get_datastore().find(query, PROPERTIES,
                                                     byte_arrays=True)

        for entry in entries:
            entry['mountpoint'] = '/'

        return entries, total_count

class InplaceResultSet(BaseResultSet):
    """Encapsulates the result of a query on a mount point
    """
    def __init__(self, query, page_size, mount_point):
        BaseResultSet.__init__(self, query, page_size)
        self._mount_point = mount_point
        self._file_list = None
        self._pending_directories = 0
        self._stopped = False

        query_text = query.get('query', '')
        if query_text.startswith('"') and query_text.endswith('"'):
            self._regex = re.compile('*%s*' % query_text.strip(['"']))
        elif query_text:
            expression = ''
            for word in query_text.split(' '):
                expression += '(?=.*%s.*)' % word
            self._regex = re.compile(expression, re.IGNORECASE)
        else:
            self._regex = None

        if query.get('timestamp', ''):
            self._date_start = int(query['timestamp']['start'])
            self._date_end = int(query['timestamp']['end'])
        else:
            self._date_start = None
            self._date_end = None

        self._mime_types = query.get('mime_type', [])

    def setup(self):
        self._file_list = []
        self._recurse_dir(self._mount_point)

    def stop(self):
        self._stopped = True

    def setup_ready(self):
        self._file_list.sort(lambda a, b: b[2] - a[2])
        self.ready.send(self)

    def find(self, query):
        if self._file_list is None:
            raise ValueError('Need to call setup() first')

        if self._stopped:
            raise ValueError('InplaceResultSet already stopped')

        t = time.time()

        offset = int(query.get('offset', 0))
        limit  = int(query.get('limit', len(self._file_list)))
        total_count = len(self._file_list)

        files = self._file_list[offset:offset + limit]

        entries = []
        for file_path, stat, mtime_ in files:
            metadata = _get_file_metadata(file_path, stat)
            metadata['mountpoint'] = self._mount_point
            entries.append(metadata)

        logging.debug('InplaceResultSet.find took %f s.', time.time() - t)

        return entries, total_count

    def _recurse_dir(self, dir_path):
        if self._stopped:
            return

        for entry in os.listdir(dir_path):
            if entry.startswith('.'):
                continue
            full_path = dir_path + '/' + entry
            try:
                stat = os.stat(full_path)
                if S_IFMT(stat.st_mode) == S_IFDIR:
                    self._pending_directories += 1
                    gobject.idle_add(lambda s=full_path: self._recurse_dir(s))

                elif S_IFMT(stat.st_mode) == S_IFREG:
                    add_to_list = True

                    if self._regex is not None and \
                            not self._regex.match(full_path):
                        add_to_list = False

                    if None not in [self._date_start, self._date_end] and \
                            (stat.st_mtime < self._date_start or
                             stat.st_mtime > self._date_end):
                        add_to_list = False

                    if self._mime_types:
                        mime_type = gio.content_type_guess(filename=full_path)
                        if mime_type not in self._mime_types:
                            add_to_list = False

                    if add_to_list:
                        file_info = (full_path, stat, int(stat.st_mtime))
                        self._file_list.append(file_info)

                    self.progress.send(self)

            except Exception:
                logging.exception('Error reading file %r', full_path)

        if self._pending_directories == 0:
            self.setup_ready()
        else:
            self._pending_directories -= 1

def _get_file_metadata(path, stat):
    client = gconf.client_get_default()
    return {'uid': path,
            'title': os.path.basename(path),
            'timestamp': stat.st_mtime,
            'mime_type': gio.content_type_guess(filename=path),
            'activity': '',
            'activity_id': '',
            'icon-color': client.get_string('/desktop/sugar/user/color'),
            'description': path}

_datastore = None
def _get_datastore():
    global _datastore
    if _datastore is None:
        bus = dbus.SessionBus()
        remote_object = bus.get_object(DS_DBUS_SERVICE, DS_DBUS_PATH)
        _datastore = dbus.Interface(remote_object, DS_DBUS_INTERFACE)

        _datastore.connect_to_signal('Created', _datastore_created_cb)
        _datastore.connect_to_signal('Updated', _datastore_updated_cb)
        _datastore.connect_to_signal('Deleted', _datastore_deleted_cb)

    return _datastore

def _datastore_created_cb(object_id):
    created.send(None, object_id=object_id)

def _datastore_updated_cb(object_id):
    updated.send(None, object_id=object_id)

def _datastore_deleted_cb(object_id):
    deleted.send(None, object_id=object_id)

def find(query, page_size):
    """Returns a ResultSet
    """
    if 'order_by' not in query:
        query['order_by'] = ['-mtime']
    
    mount_points = query.pop('mountpoints', ['/'])
    if mount_points is None or len(mount_points) != 1:
        raise ValueError('Exactly one mount point must be specified')

    if mount_points[0] == '/':
        return DatastoreResultSet(query, page_size)
    else:
        return InplaceResultSet(query, page_size, mount_points[0])

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
        stat = os.stat(object_id)
        metadata = _get_file_metadata(object_id, stat)
        metadata['mountpoint'] = _get_mount_point(object_id)
    else:
        metadata = _get_datastore().get_properties(object_id, byte_arrays=True)
        metadata['mountpoint'] = '/'
    return metadata

def get_file(object_id):
    """Returns the file for an object
    """
    if os.path.exists(object_id):
        logging.debug('get_file asked for file with path %r', object_id)
        return object_id
    else:
        logging.debug('get_file asked for entry with id %r', object_id)
        file_path = _get_datastore().get_filename(object_id)
        if file_path:
            return util.TempFilePath(file_path)
        else:
            return None

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
    file_path = get_file(metadata['uid'])

    metadata['mountpoint'] = mount_point
    del metadata['uid']

    return write(metadata, file_path)

def write(metadata, file_path='', update_mtime=True):
    """Creates or updates an entry for that id
    """
    logging.debug('model.write %r %r %r', metadata.get('uid', ''), file_path,
        update_mtime)
    if update_mtime:
        metadata['mtime'] = datetime.now().isoformat()
        metadata['timestamp'] = int(time.time())

    if metadata.get('mountpoint', '/') == '/':
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
        if not os.path.exists(file_path):
            raise ValueError('Entries without a file cannot be copied to '
                             'removable devices')

        file_name = _get_file_name(metadata['title'], metadata['mime_type'])
        file_name = _get_unique_file_name(metadata['mountpoint'], file_name)

        destination_path = os.path.join(metadata['mountpoint'], file_name)
        shutil.copy(file_path, destination_path)
        object_id = destination_path

    return object_id

def _get_file_name(title, mime_type):
    file_name = title

    extension = mime.get_primary_extension(mime_type)
    if extension is not None and extension:
        extension = '.' + extension
        if not file_name.endswith(extension):
            file_name += extension

    # Invalid characters in VFAT filenames. From
    # http://en.wikipedia.org/wiki/File_Allocation_Table
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|', '\x7F']
    invalid_chars.extend([chr(x) for x in range(0, 32)])
    for char in invalid_chars:
        file_name = file_name.replace(char, '_')

    # FAT limit is 255, leave some space for uniqueness
    max_len = 250
    if len(file_name) > max_len:
        name, extension = os.path.splitext(file_name)
        file_name = name[0:max_len - len(extension)] + extension
    
    return file_name

def _get_unique_file_name(mount_point, file_name):
    if os.path.exists(os.path.join(mount_point, file_name)):
        i = 1
        while len(file_name) <= 255:
            name, extension = os.path.splitext(file_name)
            file_name = name + '_' + str(i) + extension
            if not os.path.exists(os.path.join(mount_point, file_name)):
                break
            i += 1

    return file_name

created = dispatch.Signal()
updated = dispatch.Signal()
deleted = dispatch.Signal()

