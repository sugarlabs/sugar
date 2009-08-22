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

import gtk
import cairo
from gobject import property, GObject, SIGNAL_RUN_FIRST, TYPE_PYOBJECT

from sugar import util

from jarabe.journal.browse.lazymodel import LazyModel
from jarabe.journal import model

class Source(GObject):
    FIELD_UID = 0
    FIELD_TITLE = 1
    FIELD_MTIME = 2
    FIELD_TIMESTAMP = 3
    FIELD_KEEP = 4
    FIELD_BUDDIES = 5
    FIELD_ICON_COLOR = 6
    FIELD_MIME_TYPE = 7
    FIELD_PROGRESS = 8
    FIELD_ACTIVITY = 9
    FIELD_MOUNT_POINT = 10
    FIELD_ACTIVITY_ID = 11
    FIELD_BUNDLE_ID = 12

    FIELD_FAVORITE = 30
    FIELD_MODIFY_TIME = 31
    FIELD_THUMB = 32

    FIELDS_BASE = {'uid': (FIELD_UID, str),
                   'title': (FIELD_TITLE, str),
                   'mtime': (FIELD_MTIME, str),
                   'timestamp': (FIELD_TIMESTAMP, int),
                   'keep': (FIELD_KEEP, int),
                   'buddies': (FIELD_BUDDIES, str),
                   'icon-color': (FIELD_ICON_COLOR, str),
                   'mime_type': (FIELD_MIME_TYPE, str),
                   'progress': (FIELD_MIME_TYPE, str),
                   'activity': (FIELD_ACTIVITY, str),
                   'mountpoint': (FIELD_ACTIVITY, str),
                   'activity_id': (FIELD_ACTIVITY_ID, str),
                   'bundle_id': (FIELD_BUNDLE_ID, str)}

    FIELDS_CALC = {'favorite': (FIELD_FAVORITE, bool),
                   'modify_time': (FIELD_MODIFY_TIME, str),
                   'thumb': (FIELD_THUMB, cairo.ImageSurface)}

class LocalSource(Source):
    __gsignals__ = {
            'objects-updated': (SIGNAL_RUN_FIRST, None, []),
            'row-delayed-fetch': (SIGNAL_RUN_FIRST, None, 2*[TYPE_PYOBJECT])
            }

    def __init__(self, resultset):
        Source.__init__(self)
        self._resultset = resultset

    def get_count(self):
        return self._resultset.length

    def get_row(self, offset):
        if offset >= self.get_count():
            return False
        self._resultset.seek(offset)
        return self._resultset.read()

    def get_order(self):
        """ Get current order, returns (field_name, gtk.SortType) """
        pass

    def set_order(self, field_name, sort_type):
        """ Set current order """
        pass

    def get_object(self, metadata, cb):
        model.get(metadata['uid'], cb)
        return None
