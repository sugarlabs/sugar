# Copyright (C) 2013, Gonzalo Odiard
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

from gi.repository import GObject
from gi.repository import Gtk

from gettext import gettext as _

from jarabe.journal import model

DS_DBUS_SERVICE = 'org.laptop.sugar.DataStore'
DS_DBUS_INTERFACE = 'org.laptop.sugar.DataStore'
DS_DBUS_PATH = '/org/laptop/sugar/DataStore'


class IconModel(GObject.GObject, Gtk.TreeModel, Gtk.TreeDragSource):
    __gtype_name__ = 'JournalIconModel'

    __gsignals__ = {
        'ready': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'progress': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    COLUMN_UID = 0
    COLUMN_TITLE = 1
    COLUMN_PREVIEW = 2

    _COLUMN_TYPES = {
        COLUMN_UID: str,
        COLUMN_TITLE: str,
        COLUMN_PREVIEW: str,
    }

    _PAGE_SIZE = 100

    def __init__(self, query):
        GObject.GObject.__init__(self)

        self._last_requested_index = None
        self._cached_row = None
        self._result_set = model.find(query, IconModel._PAGE_SIZE)
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
        return model.get(self[path][IconModel.COLUMN_UID])

    def do_get_n_columns(self):
        return len(IconModel._COLUMN_TYPES)

    def do_get_column_type(self, index):
        return IconModel._COLUMN_TYPES[index]

    def do_iter_n_children(self, iterator):
        if iterator is None:
            return self._result_set.length
        else:
            return 0

    def do_get_value(self, iterator, column):
        if self.view_is_resizing:
            return None

        index = iterator.user_data
        if index == self._last_requested_index:
            return self._cached_row[column]

        if index >= self._result_set.length:
            return None

        self._result_set.seek(index)
        metadata = self._result_set.read()

        self._last_requested_index = index
        self._cached_row = []
        self._cached_row.append(metadata['uid'])

        title = GObject.markup_escape_text(metadata.get('title',
                                                        _('Untitled')))
        self._cached_row.append(title)

        self._cached_row.append(metadata.get('preview', ''))

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
        else:
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
