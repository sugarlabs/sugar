# Copyright (C) 2009, Tomeu Vizoso
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

import json
import gobject
import gtk

from sugar.graphics.xocolor import XoColor
from sugar.graphics import style
from sugar import util

from jarabe.journal import model
from jarabe.journal import misc

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'

class ListModel(gtk.GenericTreeModel, gtk.TreeDragSource):
    __gtype_name__ = 'JournalListModel'

    __gsignals__ = {
        'ready':    (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE,
                     ([])),
        'progress': (gobject.SIGNAL_RUN_FIRST,
                     gobject.TYPE_NONE,
                     ([])),
    }

    COLUMN_UID = 0
    COLUMN_FAVORITE = 1
    COLUMN_ICON = 2
    COLUMN_ICON_COLOR = 3
    COLUMN_TITLE = 4
    COLUMN_DATE = 5
    COLUMN_PROGRESS = 6
    COLUMN_BUDDY_1 = 7
    COLUMN_BUDDY_2 = 8
    COLUMN_BUDDY_3 = 9

    _COLUMN_TYPES = {COLUMN_UID:            str,
                     COLUMN_FAVORITE:       bool,
                     COLUMN_ICON:           str,
                     COLUMN_ICON_COLOR:     object,
                     COLUMN_TITLE:          str,
                     COLUMN_DATE:           str,
                     COLUMN_PROGRESS:       int,
                     COLUMN_BUDDY_1:        object,
                     COLUMN_BUDDY_3:        object,
                     COLUMN_BUDDY_2:        object}

    _PAGE_SIZE = 10

    def __init__(self, query):
        gobject.GObject.__init__(self)

        self._last_requested_index = None
        self._cached_row = None
        self._result_set = model.find(query, ListModel._PAGE_SIZE)
        self._temp_drag_file_path = None

        # HACK: The view will tell us that it is resizing so the model can
        # avoid hitting D-Bus and disk.
        self.view_is_resizing = False

        self._result_set.ready.connect(self.__result_set_ready_cb)
        self._result_set.progress.connect(self.__result_set_progress_cb)

    def __result_set_ready_cb(self, **kwargs):
        self.emit('ready')

    def __result_set_progress_cb(self, **kwargs):
        self.emit('progress')

    def setup(self):
        self._result_set.setup()

    def stop(self):
        self._result_set.stop()

    def get_metadata(self, path):
        return model.get(self[path][ListModel.COLUMN_UID])

    def on_get_n_columns(self):
        return len(ListModel._COLUMN_TYPES)

    def on_get_column_type(self, index):
        return ListModel._COLUMN_TYPES[index]

    def on_iter_n_children(self, iter):
        if iter == None:
            return self._result_set.length
        else:
            return 0

    def on_get_value(self, index, column):
        if self.view_is_resizing:
            return None

        if index == self._last_requested_index:
            return self._cached_row[column]

        if index >= self._result_set.length:
            return None

        self._result_set.seek(index)
        metadata = self._result_set.read()

        self._last_requested_index = index
        self._cached_row = []
        self._cached_row.append(metadata['uid'])
        self._cached_row.append(metadata.get('keep', '0') == '1')
        self._cached_row.append(misc.get_icon_name(metadata))

        if misc.is_activity_bundle(metadata):
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_TRANSPARENT.get_svg()))
        else:
            xo_color = misc.get_icon_color(metadata)
        self._cached_row.append(xo_color)

        title = gobject.markup_escape_text(metadata.get('title', None))
        self._cached_row.append('<b>%s</b>' % title)

        timestamp = int(metadata.get('timestamp', 0))
        self._cached_row.append(util.timestamp_to_elapsed_string(timestamp))

        self._cached_row.append(int(metadata.get('progress', 100)))

        if metadata.get('buddies', ''):
            # json cannot read unicode strings
            buddies_str = metadata['buddies'].encode('utf8')
            buddies = json.read(buddies_str).values()
        else:
            buddies = []

        for n in xrange(0, 3):
            if buddies:
                nick, color = buddies.pop(0)
                self._cached_row.append((nick, XoColor(color)))
            else:
                self._cached_row.append(None)

        return self._cached_row[column]

    def on_iter_nth_child(self, iter, n):
        return n

    def on_get_path(self, iter):
        return (iter)

    def on_get_iter(self, path):
        return path[0]

    def on_iter_next(self, iter):
        if iter != None:
            if iter >= self._result_set.length - 1:
                return None
            return iter + 1
        return None

    def on_get_flags(self):
        return gtk.TREE_MODEL_ITERS_PERSIST | gtk.TREE_MODEL_LIST_ONLY

    def on_iter_children(self, iter):
        return None

    def on_iter_has_child(self, iter):
        return False

    def on_iter_parent(self, iter):
        return None

    def do_drag_data_get(self, path, selection):
        uid = self[path][ListModel.COLUMN_UID]
        if selection.target == 'text/uri-list':
            # Get hold of a reference so the temp file doesn't get deleted
            self._temp_drag_file_path = model.get_file(uid)
            logging.debug('putting %r in selection', self._temp_drag_file_path)
            selection.set(selection.target, 8, self._temp_drag_file_path)
            return True
        elif selection.target == 'journal-object-id':
            selection.set(selection.target, 8, uid)
            return True

        return False

