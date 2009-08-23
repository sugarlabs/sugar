# Copyright (C) 2009, Aleksey Lim
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

import gobject

from sugar import util

from jarabe.journal import misc
from jarabe.journal.source import Source
from jarabe.journal.lazymodel import LazyModel


class ObjectModel(LazyModel):

    FIELD_FETCHED_FLAG = 50

    def __init__(self):
        LazyModel.__init__(self, Source.FIELDS_BASE, Source.FIELDS_CALC)
        self._fetch_queue = []
        self._object_delayed_fetch_handle = None

    def on_calc_value(self, row, column):
        if column == Source.FIELD_MODIFY_TIME:
            return util.timestamp_to_elapsed_string(
                    int(row[Source.FIELD_TIMESTAMP]) or 0)

        if column == Source.FIELD_THUMB:
            if self.fetch_metadata(row):
                return row[Source.FIELD_THUMB]
            return None

        return None

    def fetch_metadata(self, row):
        if row.metadata['mountpoint'] != '/':
            # do not process non-ds objects
            return False

        if self.FIELD_FETCHED_FLAG in row:
            return True

        if row not in self._fetch_queue:
            self._fetch_queue.append(row)
            if len(self._fetch_queue) == 1:
                gobject.idle_add(self.__idle_cb)

        return False

    def __idle_cb(self):
        while len(self._fetch_queue):
            row = self._fetch_queue[0]
            if self.in_frame(row.path[0]):
                self.source.get_object(row, self.__get_object_cb)
                break
            del self._fetch_queue[0]
        return False

    def __get_object_cb(self, metadata):
        row = self._fetch_queue[0]
        del self._fetch_queue[0]

        if metadata is not None:
            row.metadata.update(metadata)

        row[Source.FIELD_THUMB] = misc.load_preview(metadata)
        row[self.FIELD_FETCHED_FLAG] = True

        self.emit('row-changed', row.path, row.iterator)

        if len(self._fetch_queue):
            gobject.idle_add(self.__idle_cb)
