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

from sugar.datastore import datastore

# Properties the journal cares about.
PROPERTIES = ['uid', 'title', 'mtime', 'timestamp', 'keep', 'buddies',
              'icon-color', 'mime_type', 'progress', 'activity', 'mountpoint',
              'activity_id']

class _Cache(object):

    __gtype_name__ = 'query_Cache'

    def __init__(self, jobjects=None):
        self._array = []
        self._dict = {}
        if jobjects is not None:
            self.append_all(jobjects)

    def prepend_all(self, jobjects):
        for jobject in jobjects[::-1]:
            self._array.insert(0, jobject)
            self._dict[jobject.object_id] = jobject

    def append_all(self, jobjects):
        for jobject in jobjects:
            self._array.append(jobject)
            self._dict[jobject.object_id] = jobject
    
    def remove_all(self, jobjects):
        jobjects = jobjects[:]
        for jobject in jobjects:
            obj = self._dict[jobject.object_id]
            self._array.remove(obj)
            del self._dict[obj.object_id]
            obj.destroy()

    def __len__(self):
        return len(self._array)

    def __getitem__(self, key):
        if isinstance(key, basestring):
            return self._dict[key]
        else:
            return self._array[key]

    def destroy(self):
        self._destroy_jobjects(self._array)
        self._array = []
        self._dict = {}

    def _destroy_jobjects(self, jobjects):
        for jobject in jobjects:
            jobject.destroy()
        
class ResultSet(object):

    _CACHE_LIMIT = 80

    def __init__(self, query, sorting):
        self._total_count  = -1
        self._position = -1
        self._query = query
        self._sorting = sorting

        self._offset = 0
        self._cache = _Cache()

    def destroy(self):
        self._cache.destroy()

    def get_length(self):
        if self._total_count == -1:
            jobjects, self._total_count = datastore.find(self._query,
                    sorting=self._sorting,
                    limit=ResultSet._CACHE_LIMIT,
                    properties=PROPERTIES)
            self._cache.append_all(jobjects)
            self._offset = 0
        return self._total_count

    length = property(get_length)

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
            jobjects, self._total_count = datastore.find(self._query,
                    sorting=self._sorting,
                    offset=offset,
                    limit=ResultSet._CACHE_LIMIT,
                    properties=PROPERTIES)

            self._cache.remove_all(self._cache)
            self._cache.append_all(jobjects)
            self._offset = offset
            
        elif remaining_forward_entries < 2 * max_count and \
             last_cached_entry < self._total_count:

            # Add one page to the end of cache
            logging.debug('appending one more page, offset: %r' % \
                          last_cached_entry)
            jobjects, self._total_count = datastore.find(self._query,
                    sorting=self._sorting,
                    offset=last_cached_entry,
                    limit=max_count,
                    properties=PROPERTIES)
            # update cache
            self._cache.append_all(jobjects)

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
            jobjects, self._total_count = datastore.find(self._query,
                    sorting=self._sorting,
                    offset=self._offset,
                    limit=limit,
                    properties=PROPERTIES)

            # update cache
            self._cache.prepend_all(jobjects)

            # apply the cache limit
            objects_excess = len(self._cache) - ResultSet._CACHE_LIMIT
            if objects_excess > 0:
                self._cache.remove_all(self._cache[-objects_excess:])
        else:
            logging.debug('cache hit and no need to grow the cache')

        first_pos = self._position - self._offset
        last_pos = self._position - self._offset + max_count
        return self._cache[first_pos:last_pos]

def find(query, sorting=None):
    if sorting is None:
        sorting = ['-mtime']
    result_set = ResultSet(query, sorting)
    return result_set

def test():
    TOTAL_ITEMS = 1000
    SCREEN_SIZE = 10

    def mock_debug(string):
        print "\tDEBUG: %s" % string
    logging.debug = mock_debug

    def mock_find(query, sorting=None, limit=None, offset=None,
                  properties=None):
        if properties is None:
            properties = []

        print "mock_find %r %r" % (offset, (offset + limit))

        if limit is None or offset is None:
            raise RuntimeError("Unimplemented test.")

        result = []
        for index in range(offset, offset + limit):
            obj = datastore.DSObject(index, datastore.DSMetadata({}), '')
            result.append(obj)

        return result, TOTAL_ITEMS
    datastore.find = mock_find

    result_set = find({})

    print "Get first page"
    objects = result_set.read(SCREEN_SIZE)
    print [obj.object_id for obj in objects]
    assert range(0, SCREEN_SIZE) == [obj.object_id for obj in objects]
    print ""

    print "Scroll to 5th item"
    result_set.seek(5)
    objects = result_set.read(SCREEN_SIZE)
    print [obj.object_id for obj in objects]
    assert range(5, SCREEN_SIZE + 5) == [obj.object_id for obj in objects]
    print ""

    print "Scroll back to beginning"
    result_set.seek(0)
    objects = result_set.read(SCREEN_SIZE)
    print [obj.object_id for obj in objects]
    assert range(0, SCREEN_SIZE) == [obj.object_id for obj in objects]
    print ""

    print "Hit PgDn five times"
    for i in range(0, 5):
        result_set.seek((i + 1) * SCREEN_SIZE)
        objects = result_set.read(SCREEN_SIZE)
        print [obj.object_id for obj in objects]
        assert range((i + 1) * SCREEN_SIZE, (i + 2) * SCREEN_SIZE) == \
               [obj.object_id for obj in objects]
    print ""

    print "Hit PgUp five times"
    for i in range(0, 5)[::-1]:
        result_set.seek(i * SCREEN_SIZE)
        objects = result_set.read(SCREEN_SIZE)
        print [obj.object_id for obj in objects]
        assert range(i * SCREEN_SIZE, (i + 1) * SCREEN_SIZE) == \
                [obj.object_id for obj in objects]
    print ""

if __name__ == "__main__":
    test()
