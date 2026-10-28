# Copyright (C) 2009, Tomeu Vizoso
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
import time

import json
from gi.repository import GObject
from gi.repository import Gtk
from gettext import gettext as _

from sugar4.graphics.xocolor import XoColor
from sugar4.graphics import style
from sugar4 import util

from jarabe.journal import model
from jarabe.journal import misc

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'


class ListModel(GObject.GObject, Gtk.TreeModel):
    __gtype_name__ = 'JournalListModel'

    __gsignals__ = {
        'ready': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    COLUMN_UID = 0
    COLUMN_FAVORITE = 1
    COLUMN_ICON = 2
    COLUMN_ICON_COLOR = 3
    COLUMN_TITLE = 4
    COLUMN_TIMESTAMP = 5
    COLUMN_CREATION_TIME = 6
    COLUMN_FILESIZE = 7
    COLUMN_PROGRESS = 8
    COLUMN_BUDDY_1 = 9
    COLUMN_BUDDY_2 = 10
    COLUMN_BUDDY_3 = 11
    COLUMN_SELECT = 12

    _COLUMN_TYPES = {
        COLUMN_UID: GObject.TYPE_STRING,
        COLUMN_FAVORITE: GObject.TYPE_BOOLEAN,
        COLUMN_ICON: GObject.TYPE_STRING,
        COLUMN_ICON_COLOR: GObject.TYPE_PYOBJECT,
        COLUMN_TITLE: GObject.TYPE_STRING,
        COLUMN_TIMESTAMP: GObject.TYPE_STRING,
        COLUMN_CREATION_TIME: GObject.TYPE_STRING,
        COLUMN_FILESIZE: GObject.TYPE_STRING,
        COLUMN_PROGRESS: GObject.TYPE_INT,
        COLUMN_BUDDY_1: GObject.TYPE_PYOBJECT,
        COLUMN_BUDDY_2: GObject.TYPE_PYOBJECT,
        COLUMN_BUDDY_3: GObject.TYPE_PYOBJECT,
        COLUMN_SELECT: GObject.TYPE_BOOLEAN,
    }

    _dummy_xo_color = None
    _dummy_buddy = []

    _PAGE_SIZE = 10

    def __init__(self, query):
        super().__init__()

        self._last_requested_index = None
        self._temp_drag_file_uid = None
        self._cached_row = None
        self._pyobject_cache = {}
        self._query = query
        self._all_ids = []
        t = time.time()
        self._result_set = model.find(query, ListModel._PAGE_SIZE)
        logging.debug('init resultset: %r', time.time() - t)
        self._temp_drag_file_path = None
        self._selected = []

        # HACK: The view will tell us that it is resizing so the model can
        # avoid hitting D-Bus and disk.
        self.view_is_resizing = False

        # Store the changes originated in the treeview so we do not need
        # to regenerate the model and stuff up the scroll position
        self._updated_entries = {}

        self._result_set.ready.connect(self.__result_set_ready_cb)
        self._result_set.progress.connect(self.__result_set_progress_cb)

    def get_all_ids(self):
        return self._all_ids

    def __result_set_ready_cb(self, **kwargs):
        t = time.time()
        self._all_ids = self._result_set.find_ids(self._query)
        logging.debug('get all ids: %r', time.time() - t)
        self.emit('ready')

    def __result_set_progress_cb(self, **kwargs):
        self.emit('progress')

    def setup(self, updated_callback=None):
        self._result_set.setup()
        self._updated_callback = updated_callback

    def stop(self):
        self._result_set.stop()

    def get_metadata(self, path):
        return model.get(self[path][ListModel.COLUMN_UID])

    def do_get_n_columns(self):
        return len(ListModel._COLUMN_TYPES)

    def do_get_column_type(self, index):
        return ListModel._COLUMN_TYPES[index]

    def do_iter_n_children(self, iterator):
        if iterator is None:
            return self._result_set.length
        return 0

    def set_value(self, iterator, column, value):
        index = iterator.user_data
        self._result_set.seek(index)
        metadata = self._result_set.read()
        if column == ListModel.COLUMN_FAVORITE:
            metadata['keep'] = value
        if column == ListModel.COLUMN_TITLE:
            metadata['title'] = value
        self._updated_entries[metadata['uid']] = metadata
        if self._updated_callback is not None:
            model.updated.disconnect(self._updated_callback)
        model.write(metadata, update_mtime=False,
                    ready_callback=self.__reconnect_updates_cb)

    def __reconnect_updates_cb(self, metadata, filepath, uid):
        if self._updated_callback is not None:
            model.updated.connect(self._updated_callback)

    def do_get_value(self, iterator, column):
        if self.view_is_resizing:
            t = ListModel._COLUMN_TYPES[column]
            if t == GObject.TYPE_STRING:
                return ""
            elif t == GObject.TYPE_BOOLEAN:
                return False
            elif t == GObject.TYPE_INT:
                return 0
            elif t == GObject.TYPE_PYOBJECT:
                if column == ListModel.COLUMN_ICON_COLOR:
                    if ListModel._dummy_xo_color is None:
                        ListModel._dummy_xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(), style.COLOR_TRANSPARENT.get_svg()))
                    return ListModel._dummy_xo_color
                return ListModel._dummy_buddy
            return None

        index = iterator.user_data
        if index == self._last_requested_index:
            return self._cached_row[column]

        if index >= self._result_set.length:
            return None

        self._result_set.seek(index)
        metadata = self._result_set.read()
        metadata.update(self._updated_entries.get(metadata['uid'], {}))

        self._last_requested_index = index
        self._cached_row = []
        self._pyobject_cache[index] = self._cached_row
        if len(self._pyobject_cache) > 200:
            self._pyobject_cache.clear()
        self._cached_row.append(metadata['uid'])
        self._cached_row.append(metadata.get('keep', '0') == '1')
        self._cached_row.append(misc.get_icon_name(metadata))

        if misc.is_activity_bundle(metadata):
            xo_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                          style.COLOR_TRANSPARENT.get_svg()))
        else:
            xo_color = misc.get_icon_color(metadata)
        self._cached_row.append(xo_color)

        title = GObject.markup_escape_text(metadata.get('title',
                                                        _('Untitled')))
        self._cached_row.append('<b>%s</b>' % (title, ))

        try:
            timestamp = float(metadata.get('timestamp', 0))
        except (TypeError, ValueError):
            timestamp_content = _('Unknown')
        else:
            timestamp_content = util.timestamp_to_elapsed_string(timestamp)
        self._cached_row.append(timestamp_content)

        try:
            creation_time = float(metadata.get('creation_time'))
        except (TypeError, ValueError):
            self._cached_row.append(_('Unknown'))
        else:
            self._cached_row.append(
                util.timestamp_to_elapsed_string(float(creation_time)))

        try:
            size = int(metadata.get('filesize'))
        except (TypeError, ValueError):
            size = None
        self._cached_row.append(util.format_size(size))

        try:
            progress = int(float(metadata.get('progress', 100)))
        except (TypeError, ValueError):
            progress = 100
        self._cached_row.append(progress)

        buddies = []
        if metadata.get('buddies'):
            try:
                buddies = list(json.loads(metadata['buddies']).values())
            except json.decoder.JSONDecodeError as exception:
                logging.warning('Cannot decode buddies for %r: %s',
                                metadata['uid'], exception)

        if not isinstance(buddies, list):
            logging.warning('Content of buddies for %r is not a list: %r',
                            metadata['uid'], buddies)
            buddies = []

        for n_ in range(0, 3):
            if buddies:
                try:
                    nick, color = buddies.pop(0)
                except (AttributeError, ValueError) as exception:
                    logging.warning('Malformed buddies for %r: %s',
                                    metadata['uid'], exception)
                else:
                    self._cached_row.append([nick, XoColor(color)])
                    continue

            self._cached_row.append(ListModel._dummy_buddy)

        self._cached_row.append(self.is_selected(metadata['uid']))

        return self._cached_row[column]

    def do_iter_nth_child(self, parent_iter, n):
        return (False, None)

    def do_get_path(self, iterator):
        treepath = Gtk.TreePath((iterator.user_data,))
        return treepath

    def do_get_iter(self, path):
        idx = path.get_indices()[0]
        iterator = Gtk.TreeIter()
        iterator.user_data = idx
        return (True, iterator)

    def do_iter_next(self, iterator):
        idx = iterator.user_data + 1
        if idx >= self._result_set.length:
            iterator.stamp = -1
            return (False, iterator)
        iterator.user_data = idx
        return (True, iterator)

    def do_get_flags(self):
        return Gtk.TreeModelFlags.ITERS_PERSIST | Gtk.TreeModelFlags.LIST_ONLY

    def do_iter_children(self, iterator):
        return (False, iterator)

    def do_iter_has_child(self, iterator):
        return False

    def do_iter_parent(self, iterator):
        return (False, Gtk.TreeIter())

    def set_selected(self, uid, value):
        if value:
            self._selected.append(uid)
        else:
            self._selected.remove(uid)

    def is_selected(self, uid):
        return uid in self._selected

    def get_selected_items(self):
        return self._selected

    def restore_selection(self, selected):
        self._selected = selected

    def select_all(self):
        self._selected = self._all_ids[:]

    def select_none(self):
        self._selected = []
