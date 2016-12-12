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

import logging
import time
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import GLib

from jarabe.journal.iconmodel import IconModel
from sugar3.graphics.icon import Icon
from jarabe.journal import model
from sugar3.graphics.objectchooser import get_preview_pixbuf
from sugar3.graphics import style
from sugar3.activity.activity import PREVIEW_SIZE


class PreviewRenderer(Gtk.CellRendererPixbuf):

    def __init__(self, **kwds):
        Gtk.CellRendererPixbuf.__init__(self, **kwds)
        self._preview_data = None

    def set_preview_data(self, data):
        self._preview_data = data

    def do_render(self, cr, widget, background_area, cell_area, flags):
        self.props.pixbuf = get_preview_pixbuf(self._preview_data)
        Gtk.CellRendererPixbuf.do_render(self, cr, widget, background_area,
                                         cell_area, flags)

    def do_get_size(self, widget, cell_area):
        x_offset, y_offset, width, height = Gtk.CellRendererPixbuf.do_get_size(
            self, widget, cell_area)
        width = PREVIEW_SIZE[0]
        height = PREVIEW_SIZE[1]
        return (x_offset, y_offset, width, height)


class PreviewIconView(Gtk.IconView):

    def __init__(self, title_col, preview_col):
        Gtk.IconView.__init__(self)

        self._preview_col = preview_col
        self._title_col = title_col

        self.set_spacing(3)

        _preview_renderer = PreviewRenderer()
        _preview_renderer.set_alignment(0.5, 0.5)
        self.pack_start(_preview_renderer, False)
        self.set_cell_data_func(_preview_renderer,
                                self._preview_data_func, None)

        _title_renderer = Gtk.CellRendererText()
        _title_renderer.set_alignment(0.5, 0.5)
        self.pack_start(_title_renderer, True)
        self.set_cell_data_func(_title_renderer,
                                self._title_data_func, None)

    def _preview_data_func(self, view, cell, store, i, data):
        preview_data = store.get_value(i, self._preview_col)
        cell.set_preview_data(preview_data)

    def _title_data_func(self, view, cell, store, i, data):
        title = store.get_value(i, self._title_col)
        cell.props.markup = title


class IconView(Gtk.Bin):
    __gtype_name__ = 'JournalBaseIconView'

    __gsignals__ = {
        'clear-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'entry-activated': (GObject.SignalFlags.RUN_FIRST,
                            None, ([str])),
    }

    def __init__(self, toolbar):
        self._query = {}
        self._model = None
        self._progress_bar = None
        self._last_progress_bar_pulse = None
        self._scroll_position = 0.
        self._toolbar = toolbar

        Gtk.Bin.__init__(self)

        self.connect('map', self.__map_cb)
        self.connect('unrealize', self.__unrealize_cb)
        self.connect('destroy', self.__destroy_cb)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self.add(self._scrolled_window)
        self._scrolled_window.show()

        self.icon_view = PreviewIconView(IconModel.COLUMN_TITLE,
                                         IconModel.COLUMN_PREVIEW)
        self.icon_view.connect('item-activated', self.__item_activated_cb)

        self.icon_view.connect('button-release-event',
                               self.__button_release_event_cb)

        self._scrolled_window.add(self.icon_view)
        self.icon_view.show()

        # Auto-update stuff
        self._fully_obscured = True
        self._dirty = False
        self._refresh_idle_handler = None

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)

    def __button_release_event_cb(self, icon_view, event):
        path = icon_view.get_path_at_pos(int(event.x), int(event.y))
        if path is None:
            return False
        uid = icon_view.get_model()[path][IconModel.COLUMN_UID]
        self.emit('entry-activated', uid)
        return False

    def __item_activated_cb(self, icon_view, path):
        uid = icon_view.get_model()[path][IconModel.COLUMN_UID]
        self.emit('entry-activated', uid)

    def _thumb_data_func(self, view, cell, store, i, data):
        preview_data = store.get_value(i, IconModel.COLUMN_PREVIEW)
        cell.props.pixbuf = get_preview_pixbuf(preview_data)

    def __model_created_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def __model_updated_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def __model_deleted_cb(self, sender, signal, object_id):
        if self._is_new_item_visible(object_id):
            self._set_dirty()

    def _is_new_item_visible(self, object_id):
        """Check if the created item is part of the currently selected view"""
        if self._query['mountpoints'] == ['/']:
            return not object_id.startswith('/')
        else:
            return object_id.startswith(self._query['mountpoints'][0])

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)
        self.get_child().size_allocate(allocation)

    def __destroy_cb(self, widget):
        if self._model is not None:
            self._model.stop()

    def update_with_query(self, query_dict):
        if 'order_by' not in query_dict:
            query_dict['order_by'] = ['+timestamp']
        self._query = query_dict
        self.refresh()

    def refresh(self):
        self._stop_progress_bar()

        if self._model is not None:
            self._model.stop()
        self._dirty = False

        self._model = IconModel(self._query)
        self._model.connect('ready', self.__model_ready_cb)
        self._model.connect('progress', self.__model_progress_cb)
        self._model.setup()

    def __model_ready_cb(self, tree_model):
        self._stop_progress_bar()

        self._scroll_position = self.icon_view.props.vadjustment.props.value
        logging.debug('IconView.__model_ready_cb %r', self._scroll_position)

        # Cannot set it up earlier because will try to access the model
        # and it needs to be ready.
        self.icon_view.set_model(self._model)

        self.icon_view.props.vadjustment.props.value = self._scroll_position
        self.icon_view.props.vadjustment.value_changed()

        if len(tree_model) == 0:
            documents_path = model.get_documents_path()
            if self._is_query_empty():
                if self._query['mountpoints'] == ['/']:
                    self._show_message(_('Your Journal is empty'))
                elif documents_path and self._query['mountpoints'] == \
                        [documents_path]:
                    self._show_message(_('Your documents folder is empty'))
                else:
                    self._show_message(_('The device is empty'))
            else:
                self._show_message(
                    _('No matching entries'),
                    show_clear_query=self._toolbar.is_filter_changed())
        else:
            self._clear_message()

    def __map_cb(self, widget):
        logging.debug('IconView.__map_cb %r', self._scroll_position)
        self.icon_view.props.vadjustment.props.value = self._scroll_position
        self.icon_view.props.vadjustment.value_changed()

    def __unrealize_cb(self, widget):
        self._scroll_position = self.icon_view.props.vadjustment.props.value
        logging.debug('IconView.__map_cb %r', self._scroll_position)

    def _is_query_empty(self):
        # FIXME: This is a hack, we shouldn't have to update this every time
        # a new search term is added.
        return not (self._query.get('query') or self._query.get('mime_type') or
                    self._query.get('keep') or self._query.get('mtime') or
                    self._query.get('activity'))

    def __model_progress_cb(self, tree_model):
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

        if show_clear_query:
            button_box = Gtk.HButtonBox()
            button_box.set_layout(Gtk.ButtonBoxStyle.CENTER)
            box.pack_start(button_box, False, True, 0)
            button_box.show()

            button = Gtk.Button(label=_('Clear search'))
            button.connect('clicked', self.__clear_button_clicked_cb)
            button.props.image = Icon(icon_name='dialog-cancel',
                                      pixel_size=style.SMALL_ICON_SIZE)
            button_box.pack_start(button, expand=True, fill=False, padding=0)

        background_box.show_all()

    def __clear_button_clicked_cb(self, button):
        self.emit('clear-clicked')

    def _clear_message(self):
        if self.get_child() == self._scrolled_window:
            return
        self.remove(self.get_child())
        self.add(self._scrolled_window)
        self._scrolled_window.show()

    def _set_dirty(self):
        if self._fully_obscured:
            self._dirty = True
        else:
            self.refresh()

    def set_is_visible(self, visible):
        if visible != self._fully_obscured:
            return

        logging.debug('canvas_visibility_notify_event_cb %r', visible)
        if visible:
            self._fully_obscured = False
            if self._dirty:
                self.refresh()
        else:
            self._fully_obscured = True
