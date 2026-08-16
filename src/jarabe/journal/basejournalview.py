# Copyright (C) 2026, Sugar Labs (Shubham Sharma)
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

# Plumbing shared by listview.py's BaseListView and gridview.py's
# GridView: progress bar, dirty/refresh bookkeeping, and selection.

from gettext import gettext as _
import time

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import Icon

from jarabe.journal.listmodel import ListModel
from jarabe.journal import model


class BaseJournalView(Gtk.Bin):
    __gtype_name__ = 'JournalBaseView'

    __gsignals__ = {
        'clear-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self):
        self._query = {}
        self._model = None
        self._progress_bar = None
        self._last_progress_bar_pulse = None
        self._fully_obscured = True
        self._updates_disabled = False
        self._dirty = False
        self._dirty_new_query = False
        self._carried_selected = None
        # Cleared the moment a rebuild is queued: model.py's InplaceResultSet
        # can still be scanning when _do_refresh returns.
        self._model_ready = False

        Gtk.Bin.__init__(self)

    def _is_query_empty(self):
        # FIXME: This is a hack, we shouldn't have to update this every time
        # a new search term is added.
        return not (self._query.get('query') or
                    self._query.get('mime_type') or
                    self._query.get('keep') or self._query.get('mtime') or
                    self._query.get('activity'))

    def get_projects_view_active(self):
        return False

    def _connect_model_signals(self):
        model.created.connect(self.__model_created_cb)
        model.deleted.connect(self.__model_deleted_cb)

    def __model_created_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def __model_deleted_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def _is_new_item_visible(self, object_id):
        if not self._query.get('mountpoints', None):
            return None
        if self._query['mountpoints'] == ['/']:
            return not object_id.startswith('/')
        return object_id.startswith(self._query['mountpoints'][0])

    def _model_progress_cb(self, list_model):
        if self._progress_bar is None:
            self._start_progress_bar()

        if time.time() - self._last_progress_bar_pulse > 0.05:
            self._progress_bar.pulse()
            self._last_progress_bar_pulse = time.time()

    def _start_progress_bar(self):
        alignment = Gtk.Alignment.new(xalign=0.5, yalign=0.5,
                                      xscale=0.5, yscale=0)
        self.remove(self.get_child())
        self.add(alignment)
        alignment.show()

        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.props.pulse_step = 0.01
        self._last_progress_bar_pulse = time.time()
        alignment.add(self._progress_bar)
        self._progress_bar.show()

    def _stop_progress_bar(self):
        if self._progress_bar is None:
            return
        self.remove(self.get_child())
        self.add(self._scrolled_window)
        self._progress_bar = None

    def _show_message(self, message, show_clear_query=False):
        if self.get_child() is not None:
            self.remove(self.get_child())

        background_box = Gtk.EventBox()
        background_box.modify_bg(Gtk.StateType.NORMAL,
                                 style.COLOR_WHITE.get_gdk_color())
        self.add(background_box)

        alignment = Gtk.Alignment.new(0.5, 0.5, 0.1, 0.1)
        background_box.add(alignment)

        box = Gtk.VBox()
        alignment.add(box)

        icon = Icon(pixel_size=style.LARGE_ICON_SIZE,
                    icon_name='activity-journal',
                    stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                    fill_color=style.COLOR_TRANSPARENT.get_svg())
        box.pack_start(icon, expand=True, fill=False, padding=0)

        label = Gtk.Label()
        color = style.COLOR_BUTTON_GREY.get_html()
        label.set_markup('<span weight="bold" color="%s">%s</span>' % (
            color, GLib.markup_escape_text(message)))
        box.pack_start(label, expand=True, fill=False, padding=0)

        if not self.get_projects_view_active():
            if show_clear_query:
                button_box = Gtk.HButtonBox()
                button_box.set_layout(Gtk.ButtonBoxStyle.CENTER)
                box.pack_start(button_box, False, True, 0)
                button_box.show()

                button = Gtk.Button(label=_('Clear search'))
                button.connect('clicked', self.__clear_button_clicked_cb)
                button.props.image = Icon(icon_name='dialog-cancel',
                                          pixel_size=style.SMALL_ICON_SIZE)
                button_box.pack_start(button, expand=True, fill=False,
                                      padding=0)

        background_box.show_all()

    def __clear_button_clicked_cb(self, button):
        self.emit('clear-clicked')

    def _clear_message(self):
        if self.get_child() == self._scrolled_window:
            return
        if self.get_child() is not None:
            self.remove(self.get_child())
        self.add(self._scrolled_window)
        self._scrolled_window.show()

    def _set_dirty(self):
        if self._fully_obscured or self._updates_disabled:
            self._dirty = True
        else:
            self.refresh()

    def disable_updates(self):
        self._updates_disabled = True

    def enable_updates(self):
        self._updates_disabled = False
        if self._dirty:
            self.refresh(self._dirty_new_query)

    def set_is_visible(self, visible):
        if visible != self._fully_obscured:
            return
        if visible:
            self._fully_obscured = False
            if self._dirty:
                self.refresh(self._dirty_new_query)
        else:
            self._fully_obscured = True

    def _defer_refresh(self, new_query):
        if self._fully_obscured:
            self._dirty = True
            self._dirty_new_query = self._dirty_new_query or new_query
            return True
        return False

    def _reset_model(self, new_query):
        if self._model is not None:
            if new_query:
                self._backup_selected = None
            else:
                self._backup_selected = self._model.get_selected_items()
            self._model.stop()
        if self._carried_selected is not None:
            self._backup_selected = self._carried_selected
            self._carried_selected = None
        self._dirty = False
        self._dirty_new_query = False
        self._model_ready = False

        self._model = ListModel(self._query)
        self._model.connect('progress', self._model_progress_cb)

    def get_model(self):
        return self._model

    def select_all(self):
        self.get_model().select_all()
        self._repaint_selection()
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def select_none(self):
        self.get_model().select_none()
        self._repaint_selection()
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def carry_selection(self, selected):
        if self._model is not None:
            self._model.restore_selection(list(selected))
        if self._dirty or not self._model_ready:
            self._carried_selected = selected
            return
        self._repaint_selection()

    def _repaint_selection(self):
        raise NotImplementedError
