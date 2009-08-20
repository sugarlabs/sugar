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
from gobject import property, GObject, SIGNAL_RUN_FIRST, TYPE_PYOBJECT

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
FIELD_ICON = 31
FIELD_MODIFY_TIME = 32
FIELD_THUMB = 33

FIELDS_LIST = {'uid': (FIELD_UID, str),
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
               'bundle_id': (FIELD_BUNDLE_ID, str),

                'favorite': (FIELD_FAVORITE, bool),
               'icon': (FIELD_ICON, str),
               'modify_time': (FIELD_MODIFY_TIME, str),
               'thumb': (FIELD_THUMB, gtk.gdk.Pixbuf)}

class Source(GObject):
    __gsignals__ = {
            'objects-updated': (SIGNAL_RUN_FIRST, None, []),
            'row-delayed-fetch': (SIGNAL_RUN_FIRST, None, 2*[TYPE_PYOBJECT])
            }

    def get_count(self):
        """ Returns number of objects """
        pass

    def get_row(self, offset):
        """ Get object

        Returns:
            objects     in dict {field_name: value, ...}
            False       can't fint object
            None        wait for reply signal

        """
        pass

    def get_order(self):
        """ Get current order, returns (field_name, gtk.SortType) """
        pass

    def set_order(self, field_name, sort_type):
        """ Set current order """
        pass
