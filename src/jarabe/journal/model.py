# Copyright (C) 2007-2011, One Laptop per Child
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import logging
import os
import errno
import subprocess
from datetime import datetime
import time
import tempfile
from stat import S_IFLNK, S_IFMT, S_IFDIR, S_IFREG
import re
from operator import itemgetter
import json
from gettext import gettext as _

import dbus
from gi.repository import Gio
from gi.repository import GLib

from gi.repository import SugarExt

from sugar3 import dispatch
from sugar3 import mime
from sugar3 import util


DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

# Properties the journal cares about.
PROPERTIES = ['activity', 'activity_id', 'buddies', 'bundle_id',
              'creation_time', 'filesize', 'icon-color', 'keep', 'mime_type',
              'mountpoint', 'mtime', 'progress', 'timestamp', 'title', 'uid',
              'preview']

MIN_PAGES_TO_CACHE = 3
MAX_PAGES_TO_CACHE = 5

JOURNAL_METADATA_DIR = '.Sugar-Metadata'

_datastore = None
created = dispatch.Signal()
updated = dispatch.Signal()
deleted = dispatch.Signal()


class _Cache(object):

    __gtype_name__ = 'model_Cache'

    def __init__(self, entries=None):
        self._array = []
        if entries is not None:
            self.append_all(entries)

    def prepend_all(self, entries):
        self._array[0:0] = entries

    def append_all(self, entries):
        self._array += entries

    def __len__(self):
        return len(self._array)

    def __getitem__(self, key):
        return self._array[key]

    def __delitem__(self, key):
        del self._array[key]


class BaseResultSet(object):
    """Encapsulates the result of a query
    """

    def __init__(self, query, page_size):
        self._total_count = -1
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

            del self._cache[:]
            self._cache.append_all(entries)
            self._offset = offset

        elif (remaining_forward_entries <= 0 and
              remaining_backwards_entries > 0):

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
                del self._cache[:objects_excess]

        elif remaining_forward_entries > 0 and \
                remaining_backwards_entries <= 0 and self._offset > 0:

            # Add one page to the beginning of cache
            limit = min(self._offset, self._page_size)
            self._offset = max(0, self._offset - limit)

            logging.debug('prepending one more page, offset: %r limit: %r',
                          self._offset, limit)
            query = self._query.copy()
            query['limit'] = limit
            query['offset'] = self._offset
            entries, self._total_count = self.find(query)

            # update cache
            self._cache.prepend_all(entries)

            # apply the cache limit
            cache_limit = self._page_size * MAX_PAGES_TO_CACHE
            objects_excess = len(self._cache) - cache_limit
            if objects_excess > 0:
                del self._cache[-objects_excess:]

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

    def find_ids(self, query):
        copy = query.copy()
        copy.pop('mountpoints', '/')
        return _get_datastore().find_ids(copy)


class InplaceResultSet(BaseResultSet):
    """Encapsulates the result of a query on a mount point
    """

    def __init__(self, query, page_size, mount_point):
        BaseResultSet.__init__(self, query, page_size)
        self._mount_point = mount_point
        self._file_list = None
        self._pending_directories = []
        self._visited_directories = []
        self._pending_files = []
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

        self._only_favorites = int(query.get('keep', '0')) == 1

        self._filter_by_activity = query.get('activity', '')

        self._mime_types = query.get('mime_type', [])

        self._sort = query.get('order_by', ['+timestamp'])[0]

    def setup(self):
        self._file_list = []
        self._pending_directories = [self._mount_point]
        self._visited_directories = []
        self._pending_files = []
        GLib.idle_add(self._scan)

    def stop(self):
        self._stopped = True

    def setup_ready(self):
        if self._sort[1:] == 'filesize':
            keygetter = itemgetter(3)
        else:
            # timestamp
            keygetter = itemgetter(2)
        self._file_list.sort(lambda a, b: cmp(b, a),
                             key=keygetter,
                             reverse=(self._sort[0] == '-'))
        self.ready.send(self)

    def find(self, query):
        if self._file_list is None:
            raise ValueError('Need to call setup() first')

        if self._stopped:
            raise ValueError('InplaceResultSet already stopped')

        t = time.time()

        offset = int(query.get('offset', 0))
        limit = int(query.get('limit', len(self._file_list)))
        total_count = len(self._file_list)

        files = self._file_list[offset:offset + limit]

        entries = []
        for file_path, stat, mtime_, size_, metadata in files:
            if metadata is None:
                metadata = _get_file_metadata(file_path, stat)
            metadata['mountpoint'] = self._mount_point
            entries.append(metadata)

        logging.debug('InplaceResultSet.find took %f s.', time.time() - t)

        return entries, total_count

    def find_ids(self, query):
        if self._file_list is None:
            raise ValueError('Need to call setup() first')

        if self._stopped:
            raise ValueError('InplaceResultSet already stopped')

        ids = []
        for file_path, stat, mtime_, size_, metadata in self._file_list:
            ids.append(file_path)
        return ids

    def _scan(self):
        if self._stopped:
            return False

        self.progress.send(self)

        if self._pending_files:
            self._scan_a_file()
            return True

        if self._pending_directories:
            self._scan_a_directory()
            return True

        self.setup_ready()
        self._visited_directories = []
        return False

    def _scan_a_file(self):
        full_path = self._pending_files.pop(0)
        metadata = None

        try:
            stat = os.lstat(full_path)
        except OSError as e:
            if e.errno != errno.ENOENT:
                logging.exception(
                    'Error reading metadata of file %r', full_path)
            return

        if S_IFMT(stat.st_mode) == S_IFLNK:
            try:
                link = os.readlink(full_path)
            except OSError as e:
                logging.exception(
                    'Error reading target of link %r', full_path)
                return

            if not os.path.abspath(link).startswith(self._mount_point):
                return

            try:
                stat = os.stat(full_path)

            except OSError as e:
                if e.errno != errno.ENOENT:
                    logging.exception(
                        'Error reading metadata of linked file %r', full_path)
                return

        if S_IFMT(stat.st_mode) == S_IFDIR:
            id_tuple = stat.st_ino, stat.st_dev
            if id_tuple not in self._visited_directories:
                self._visited_directories.append(id_tuple)
                self._pending_directories.append(full_path)
            return

        if S_IFMT(stat.st_mode) != S_IFREG:
            return

        if self._regex is not None and \
                not self._regex.match(full_path):
            metadata = _get_file_metadata(full_path, stat,
                                          fetch_preview=False)
            if not metadata:
                return
            add_to_list = False
            for f in ['fulltext', 'title',
                      'description', 'tags']:
                if f in metadata and \
                        self._regex.match(metadata[f]):
                    add_to_list = True
                    break
            if not add_to_list:
                return

        if self._only_favorites:
            if not metadata:
                metadata = _get_file_metadata(full_path, stat,
                                              fetch_preview=False)
            if 'keep' not in metadata:
                return
            try:
                if int(metadata['keep']) == 0:
                    return
            except ValueError:
                return

        if self._filter_by_activity:
            if not metadata:
                metadata = _get_file_metadata(full_path, stat,
                                              fetch_preview=False)
            if 'activity' not in metadata or \
                    metadata['activity'] != self._filter_by_activity:
                return

        if self._date_start is not None and stat.st_mtime < self._date_start:
            return

        if self._date_end is not None and stat.st_mtime > self._date_end:
            return

        if self._mime_types:
            mime_type, uncertain_result_ = \
                Gio.content_type_guess(filename=full_path, data=None)
            if mime_type not in self._mime_types:
                return

        file_info = (full_path, stat, int(stat.st_mtime), stat.st_size,
                     metadata)
        self._file_list.append(file_info)

        return

    def _scan_a_directory(self):
        dir_path = self._pending_directories.pop(0)

        try:
            entries = os.listdir(dir_path)
        except OSError as e:
            if e.errno != errno.EACCES:
                logging.exception('Error reading directory %r', dir_path)
            return

        for entry in entries:
            if entry.startswith('.'):
                continue
            self._pending_files.append(dir_path + '/' + entry)
        return


def _get_file_metadata(path, stat, fetch_preview=True):
    """Return the metadata from the corresponding file.

    Reads the metadata stored in the json file or create the
    metadata based on the file properties.

    """
    metadata = _get_file_metadata_from_json(path, fetch_preview)
    if metadata:
        if 'filesize' not in metadata:
            metadata['filesize'] = stat.st_size
        return metadata

    mime_type, uncertain_result_ = Gio.content_type_guess(filename=path,
                                                          data=None)
    return {'uid': path,
            'title': os.path.basename(path),
            'timestamp': stat.st_mtime,
            'filesize': stat.st_size,
            'mime_type': mime_type,
            'activity': '',
            'activity_id': '',
            'icon-color': '#000000,#ffffff',
            'description': path}


def _get_file_metadata_from_json(path, fetch_preview):
    """Read the metadata from the json file and the preview
    stored on the external device.

    If the metadata is corrupted we do remove it and the preview as well.

    """
    filename = os.path.basename(path)
    dir_path = os.path.dirname(path)

    metadata = None
    mount_point = _get_mount_point(path)
    subdir = ''
    # check if the file is a subdirectory
    if mount_point != dir_path:
        subdir = os.path.relpath(dir_path, mount_point)

    metadata_path = os.path.join(mount_point, JOURNAL_METADATA_DIR, subdir,
                                 filename + '.metadata')
    preview_path = os.path.join(mount_point, JOURNAL_METADATA_DIR, subdir,
                                filename + '.preview')

    if not os.path.exists(metadata_path):
        return None

    try:
        metadata = json.load(open(metadata_path))
    except (ValueError, EnvironmentError):
        os.unlink(metadata_path)
        if os.path.exists(preview_path):
            os.unlink(preview_path)
        logging.error('Could not read metadata for file %r on '
                      'external device.', filename)
        return None
    else:
        metadata['uid'] = path

    if not fetch_preview:
        if 'preview' in metadata:
            del(metadata['preview'])
    else:
        if os.path.exists(preview_path):
            try:
                metadata['preview'] = dbus.ByteArray(open(preview_path).read())
            except EnvironmentError:
                logging.debug('Could not read preview for file %r on '
                              'external device.', filename)

    return metadata


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


def find(query_, page_size):
    """Returns a ResultSet
    """
    query = query_.copy()

    mount_points = query.pop('mountpoints', ['/'])
    if mount_points is None or len(mount_points) != 1:
        raise ValueError('Exactly one mount point must be specified')

    if mount_points[0] == '/':
        return DatastoreResultSet(query, page_size)
    else:
        return InplaceResultSet(query, page_size, mount_points[0])


def _get_mount_point(path):
    dir_path = os.path.dirname(path)
    documents_path = get_documents_path()
    while dir_path:
        if dir_path == documents_path:
            return documents_path
        elif os.path.ismount(dir_path):
            return dir_path
        else:
            dir_path = dir_path.rsplit(os.sep, 1)[0]
    return None


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


def get_file_size(object_id):
    """Return the file size for an object
    """
    logging.debug('get_file_size %r', object_id)
    if os.path.exists(object_id):
        return os.stat(object_id).st_size

    file_path = _get_datastore().get_filename(object_id)
    if file_path:
        size = os.stat(file_path).st_size
        os.remove(file_path)
        return size

    return 0


def get_unique_values(key):
    """Returns a list with the different values a property has taken
    """
    empty_dict = dbus.Dictionary({}, signature='ss')
    return _get_datastore().get_uniquevaluesfor(key, empty_dict)


def delete(object_id):
    """Removes an object from persistent storage
    """
    if not os.path.exists(object_id):
        _get_datastore().delete(object_id)
    else:
        os.unlink(object_id)
        dir_path = os.path.dirname(object_id)
        filename = os.path.basename(object_id)

        mount_point = _get_mount_point(object_id)
        subdir = ''
        # check if the file is a subdirectory
        if mount_point != dir_path:
            subdir = os.path.relpath(dir_path, mount_point)

        metadata_path = os.path.join(mount_point, JOURNAL_METADATA_DIR,
                                     subdir)

        old_files = [os.path.join(metadata_path, filename + '.metadata'),
                     os.path.join(metadata_path, filename + '.preview')]
        for old_file in old_files:
            if os.path.exists(old_file):
                try:
                    os.unlink(old_file)
                except EnvironmentError:
                    logging.error('Could not remove metadata=%s '
                                  'for file=%s', old_file, filename)
        try:
            os.rmdir(metadata_path)
        except:
            # if can't remove is because there are other metadata
            pass
        deleted.send(None, object_id=object_id)


def copy(metadata, mount_point, ready_callback=None):
    """Copies an object to another mount point
    """
    metadata = get(metadata['uid'])
    if mount_point == '/' and metadata.get('icon-color') == '#000000,#ffffff':
        settings = Gio.Settings('org.sugarlabs.user')
        metadata['icon-color'] = settings.get_string('color')
    file_path = get_file(metadata['uid'])
    if file_path is None:
        file_path = ''

    metadata['mountpoint'] = mount_point
    del metadata['uid']

    write(metadata, file_path, transfer_ownership=False,
          ready_callback=ready_callback)


def write(metadata, file_path='', update_mtime=True, transfer_ownership=True,
          ready_callback=None):
    """Creates or updates an entry for that id
    """
    def created_reply_handler(object_id):
        if ready_callback:
            ready_callback(metadata, file_path, object_id)

    def updated_reply_handler():
        if ready_callback:
            ready_callback(metadata, file_path, metadata['uid'])

    def error_handler(error):
        logging.error('Could not create/update datastore entry')

    logging.debug('model.write %r %r %r', metadata.get('uid', ''), file_path,
                  update_mtime)
    if update_mtime:
        metadata['mtime'] = datetime.now().isoformat()
        metadata['timestamp'] = int(time.time())

    if metadata.get('mountpoint', '/') == '/':
        if metadata.get('uid', ''):
            _get_datastore().update(metadata['uid'],
                                    dbus.Dictionary(metadata),
                                    file_path,
                                    transfer_ownership,
                                    reply_handler=updated_reply_handler,
                                    error_handler=error_handler)
        else:
            _get_datastore().create(dbus.Dictionary(metadata),
                                    file_path,
                                    transfer_ownership,
                                    reply_handler=created_reply_handler,
                                    error_handler=error_handler)
    else:
        _write_entry_on_external_device(
            metadata, file_path, ready_callback=ready_callback)


def _rename_entry_on_external_device(file_path, destination_path,
                                     metadata_dir_path):
    """Rename an entry with the associated metadata on an external device."""
    old_file_path = file_path
    if old_file_path != destination_path:
        os.rename(file_path, destination_path)
        old_fname = os.path.basename(file_path)
        old_files = [os.path.join(metadata_dir_path,
                                  old_fname + '.metadata'),
                     os.path.join(metadata_dir_path,
                                  old_fname + '.preview')]
        for ofile in old_files:
            if os.path.exists(ofile):
                try:
                    os.unlink(ofile)
                except EnvironmentError:
                    logging.error('Could not remove metadata=%s '
                                  'for file=%s', ofile, old_fname)


def _write_entry_on_external_device(metadata, file_path, ready_callback=None):
    """Create and update an entry copied from the
    DS to an external storage device.

    Besides copying the associated file a file for the preview
    and one for the metadata are stored in the hidden directory
    .Sugar-Metadata.

    This function handles renames of an entry on the
    external device and avoids name collisions. Renames are
    handled failsafe.

    """
    def _ready_cb():
        if ready_callback:
            ready_callback(metadata, file_path, destination_path)

    def _updated_cb(*args):
        updated.send(None, object_id=destination_path)
        _ready_cb()

    def _splice_cb(*args):
        created.send(None, object_id=destination_path)
        _ready_cb()

    if 'uid' in metadata and os.path.exists(metadata['uid']):
        file_path = metadata['uid']

    if not file_path or not os.path.exists(file_path):
        raise ValueError('Entries without a file cannot be copied to '
                         'removable devices')

    if not metadata.get('title'):
        metadata['title'] = _('Untitled')

    original_file_name = os.path.basename(file_path)
    original_dir_name = os.path.dirname(file_path)
    # if is a file in the exernal device or Documents
    # and the title is equal to the file name don't change it
    if original_file_name == metadata['title'] and \
            original_dir_name.startswith(metadata['mountpoint']):
        destination_path = file_path
        file_name = original_file_name
    else:
        file_name = metadata['title']
        # only change the extension if the title don't have a good extension
        clean_name, extension = os.path.splitext(file_name)
        extension = extension.replace('.', '').lower()
        mime_type = metadata.get('mime_type', None)
        if mime_type is not None:
            mime_extensions = mime.get_extensions_by_mimetype(mime_type)
            if extension not in mime_extensions:
                file_name = get_file_name(metadata['title'], mime_type)

        destination_path = os.path.join(metadata['mountpoint'], file_name)
        if destination_path != file_path:
            file_name = get_unique_file_name(metadata['mountpoint'],
                                             file_name)
            destination_path = os.path.join(metadata['mountpoint'],
                                            file_name)
            metadata['title'] = file_name

    metadata_copy = metadata.copy()
    metadata_copy.pop('mountpoint', None)
    metadata_copy.pop('uid', None)
    metadata_copy.pop('filesize', None)

    metadata_dir_path = os.path.join(metadata['mountpoint'],
                                     JOURNAL_METADATA_DIR)
    # check if the file is in a subdirectory in Documents or device
    if original_dir_name.startswith(metadata['mountpoint']) and \
            original_dir_name != metadata['mountpoint']:
        subdir = os.path.relpath(original_dir_name, metadata['mountpoint'])
        metadata_dir_path = os.path.join(metadata_dir_path, subdir)
    if not os.path.exists(metadata_dir_path):
        os.makedirs(metadata_dir_path)

    # Set the HIDDEN attrib even when the metadata directory already
    # exists for backward compatibility; but don't set it in ~/Documents
    if not metadata['mountpoint'] == get_documents_path():
        if not SugarExt.fat_set_hidden_attrib(metadata_dir_path):
            logging.error('Could not set hidden attribute on %s' %
                          (metadata_dir_path))

    preview = None
    if 'preview' in metadata_copy:
        preview = metadata_copy['preview']
        preview_fname = file_name + '.preview'
        metadata_copy.pop('preview', None)

    try:
        metadata_json = json.dumps(metadata_copy)
    except (UnicodeDecodeError, EnvironmentError):
        logging.error('Could not convert metadata to json.')
    else:
        (fh, fn) = tempfile.mkstemp(dir=metadata['mountpoint'])
        os.write(fh, metadata_json)
        os.close(fh)
        os.rename(fn, os.path.join(metadata_dir_path, file_name + '.metadata'))

        if preview:
            (fh, fn) = tempfile.mkstemp(dir=metadata['mountpoint'])
            os.write(fh, preview)
            os.close(fh)
            os.rename(fn, os.path.join(metadata_dir_path, preview_fname))

    if not os.path.dirname(destination_path) == os.path.dirname(file_path):
        input_stream = Gio.File.new_for_path(file_path).read(None)
        output_stream = Gio.File.new_for_path(destination_path)\
            .append_to(Gio.FileCreateFlags.PRIVATE |
                       Gio.FileCreateFlags.REPLACE_DESTINATION, None)

        # TODO: use Gio.File.copy_async, when implemented
        output_stream.splice_async(
            input_stream,
            Gio.OutputStreamSpliceFlags.CLOSE_SOURCE |
            Gio.OutputStreamSpliceFlags.CLOSE_TARGET,
            GLib.PRIORITY_LOW, None, _splice_cb, None)
    else:
        _rename_entry_on_external_device(file_path, destination_path,
                                         metadata_dir_path)
        _updated_cb()


def get_file_name(title, mime_type):
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


def get_unique_file_name(mount_point, file_name):
    if os.path.exists(os.path.join(mount_point, file_name)):
        i = 1
        name, extension = os.path.splitext(file_name)
        while len(file_name) <= 255:
            file_name = name + '_' + str(i) + extension
            if not os.path.exists(os.path.join(mount_point, file_name)):
                break
            i += 1

    return file_name


def is_editable(metadata):
    if metadata.get('mountpoint', '/') == '/':
        return True
    else:
        return os.access(metadata['mountpoint'], os.W_OK)


_documents_path = None


def get_documents_path():
    """Gets the path of the DOCUMENTS folder

    If xdg-user-dir can not find the DOCUMENTS folder it returns
    $HOME, which we omit. xdg-user-dir handles localization
    (i.e. translation) of the filenames.

    Returns: Path to $HOME/DOCUMENTS or None if an error occurs
    """
    global _documents_path
    if _documents_path is not None:
        return _documents_path

    try:
        pipe = subprocess.Popen(['xdg-user-dir', 'DOCUMENTS'],
                                stdout=subprocess.PIPE)
        documents_path = os.path.normpath(pipe.communicate()[0].strip())
        if os.path.exists(documents_path) and \
                os.environ.get('HOME') != documents_path:
            _documents_path = documents_path
    except OSError as exception:
        if exception.errno != errno.ENOENT:
            logging.exception('Could not run xdg-user-dir')
    return _documents_path
