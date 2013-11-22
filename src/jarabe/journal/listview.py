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
from gettext import gettext as _
import time

from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GConf
from gi.repository import Pango

from sugar3.graphics import style
from sugar3.graphics.icon import Icon, CellRendererIcon
from sugar3.graphics.xocolor import XoColor
from sugar3 import util

from jarabe.journal.listmodel import ListModel
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import model
from jarabe.journal import misc
from jarabe.journal import journalwindow


UPDATE_INTERVAL = 300


class TreeView(Gtk.TreeView):
    __gtype_name__ = 'JournalTreeView'

    def __init__(self):
        Gtk.TreeView.__init__(self)
        self.set_headers_visible(False)
        self.set_enable_search(False)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.TOUCH_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK)

    def do_size_request(self, requisition):
        # HACK: We tell the model that the view is just resizing so it can
        # avoid hitting both D-Bus and disk.
        tree_model = self.get_model()
        if tree_model is not None:
            tree_model.view_is_resizing = True
        try:
            Gtk.TreeView.do_size_request(self, requisition)
        finally:
            if tree_model is not None:
                tree_model.view_is_resizing = False


class BaseListView(Gtk.Bin):
    __gtype_name__ = 'JournalBaseListView'

    __gsignals__ = {
        'clear-clicked': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self, journalactivity, enable_multi_operations=False):
        self._query = {}
        self._journalactivity = journalactivity
        self._enable_multi_operations = enable_multi_operations
        self._model = None
        self._progress_bar = None
        self._last_progress_bar_pulse = None
        self._scroll_position = 0.

        Gtk.Bin.__init__(self)

        self.connect('map', self.__map_cb)
        self.connect('unmap', self.__unmap_cb)
        self.connect('destroy', self.__destroy_cb)

        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.NEVER,
                                         Gtk.PolicyType.AUTOMATIC)
        self.add(self._scrolled_window)
        self._scrolled_window.show()

        self.tree_view = TreeView()
        selection = self.tree_view.get_selection()
        selection.set_mode(Gtk.SelectionMode.NONE)
        self.tree_view.props.fixed_height_mode = True
        self._scrolled_window.add(self.tree_view)
        self.tree_view.show()

        self.cell_title = None
        self.cell_icon = None
        self._title_column = None
        self.sort_column = None
        self._add_columns()

        self.enable_drag_and_copy()

        # Auto-update stuff
        self._fully_obscured = True
        self._updates_disabled = False
        self._dirty = False
        self._refresh_idle_handler = None
        self._update_dates_timer = None
        self._backup_selected = None

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)

    def enable_drag_and_copy(self):
        self.tree_view.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                                [('text/uri-list', 0, 0),
                                                 ('journal-object-id', 0, 0)],
                                                Gdk.DragAction.COPY)

    def disable_drag_and_copy(self):
        self.tree_view.unset_rows_drag_source()

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

    def _add_columns(self):
        if self._enable_multi_operations:
            cell_select = Gtk.CellRendererToggle()
            cell_select.connect('toggled', self.__cell_select_toggled_cb)
            cell_select.props.activatable = True
            cell_select.props.xpad = style.DEFAULT_PADDING
            cell_select.props.indicator_size = style.zoom(26)

            column = Gtk.TreeViewColumn()
            column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
            column.props.fixed_width = style.GRID_CELL_SIZE
            column.pack_start(cell_select, True)
            column.set_cell_data_func(cell_select, self.__select_set_data_cb)
            self.tree_view.append_column(column)

        cell_favorite = CellRendererFavorite(self.tree_view)
        cell_favorite.connect('clicked', self.__favorite_clicked_cb)

        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = cell_favorite.props.width
        column.pack_start(cell_favorite, True)
        column.set_cell_data_func(cell_favorite, self.__favorite_set_data_cb)
        self.tree_view.append_column(column)

        self.cell_icon = CellRendererActivityIcon(self._journalactivity,
                                                  self.tree_view)

        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = self.cell_icon.props.width
        column.pack_start(self.cell_icon, True)
        column.add_attribute(self.cell_icon, 'file-name',
                             ListModel.COLUMN_ICON)
        column.add_attribute(self.cell_icon, 'xo-color',
                             ListModel.COLUMN_ICON_COLOR)
        self.tree_view.append_column(column)

        self.cell_title = Gtk.CellRendererText()
        self.cell_title.props.ellipsize = Pango.EllipsizeMode.MIDDLE
        self.cell_title.props.ellipsize_set = True

        self._title_column = Gtk.TreeViewColumn()
        self._title_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self._title_column.props.expand = True
        self._title_column.props.clickable = True
        self._title_column.pack_start(self.cell_title, True)
        self._title_column.add_attribute(self.cell_title, 'markup',
                                         ListModel.COLUMN_TITLE)
        self.tree_view.append_column(self._title_column)

        for column_index in [ListModel.COLUMN_BUDDY_1,
                             ListModel.COLUMN_BUDDY_2,
                             ListModel.COLUMN_BUDDY_3]:

            buddies_column = Gtk.TreeViewColumn()
            buddies_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
            self.tree_view.append_column(buddies_column)

            cell_icon = CellRendererBuddy(self.tree_view,
                                          column_index=column_index)
            buddies_column.pack_start(cell_icon, True)
            buddies_column.props.fixed_width += cell_icon.props.width
            buddies_column.add_attribute(cell_icon, 'buddy', column_index)
            buddies_column.set_cell_data_func(cell_icon,
                                              self.__buddies_set_data_cb)

        cell_progress = Gtk.CellRendererProgress()
        cell_progress.props.ypad = style.GRID_CELL_SIZE / 4
        buddies_column.pack_start(cell_progress, True)
        buddies_column.add_attribute(cell_progress, 'value',
                                     ListModel.COLUMN_PROGRESS)
        buddies_column.set_cell_data_func(cell_progress,
                                          self.__progress_data_cb)

        cell_text = Gtk.CellRendererText()
        cell_text.props.xalign = 1

        # Measure the required width for a date in the form of "10 hours, 10
        # minutes ago"
        timestamp = time.time() - 10 * 60 - 10 * 60 * 60
        date = util.timestamp_to_elapsed_string(timestamp)
        date_width = self._get_width_for_string(date)

        self.sort_column = Gtk.TreeViewColumn()
        self.sort_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self.sort_column.props.fixed_width = date_width
        self.sort_column.set_alignment(1)
        self.sort_column.props.resizable = True
        self.sort_column.props.clickable = True
        self.sort_column.pack_start(cell_text, True)
        self.sort_column.add_attribute(cell_text, 'text',
                                       ListModel.COLUMN_TIMESTAMP)
        self.tree_view.append_column(self.sort_column)

    def _get_width_for_string(self, text):
        # Add some extra margin
        text = text + 'aaaaa'

        widget = Gtk.Label(label='')
        context = widget.get_pango_context()
        layout = Pango.Layout(context)
        layout.set_text(text, len(text))
        width, height_ = layout.get_pixel_size()
        return width

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)
        self.get_child().size_allocate(allocation)

    def do_size_request(self, requisition):
        requisition.width, requisition.height = \
            self.get_child().size_request()

    def __destroy_cb(self, widget):
        if self._model is not None:
            self._model.stop()

    def __buddies_set_data_cb(self, column, cell, tree_model,
                              tree_iter, data):
        buddy = tree_model.do_get_value(tree_iter, cell._model_column_index)
        if buddy is None:
            cell.props.visible = False
            return
        # FIXME workaround for pygobject bug, see
        # https://bugzilla.gnome.org/show_bug.cgi?id=689277
        #
        # add_attribute with 'buddy' attribute in the cell should take
        # care of setting it.
        cell.props.buddy = buddy

        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        cell.props.visible = progress >= 100

    def __progress_data_cb(self, column, cell, tree_model,
                           tree_iter, data):
        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        cell.props.visible = progress < 100

    def __favorite_set_data_cb(self, column, cell, tree_model,
                               tree_iter, data):
        favorite = tree_model[tree_iter][ListModel.COLUMN_FAVORITE]
        if favorite:
            client = GConf.Client.get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            cell.props.xo_color = color
        else:
            cell.props.xo_color = None

    def __favorite_clicked_cb(self, cell, path):
        row = self._model[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        if not model.is_editable(metadata):
            return
        if metadata.get('keep', 0) == '1':
            metadata['keep'] = '0'
        else:
            metadata['keep'] = '1'
        model.write(metadata, update_mtime=False)

    def __select_set_data_cb(self, column, cell, tree_model, tree_iter,
                             data):
        uid = tree_model[tree_iter][ListModel.COLUMN_UID]
        if uid is None:
            return
        cell.props.active = self._model.is_selected(uid)

    def __cell_select_toggled_cb(self, cell, path):
        tree_iter = self._model.get_iter(path)
        uid = self._model[tree_iter][ListModel.COLUMN_UID]
        self._model.set_selected(uid, not cell.get_active())
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def update_with_query(self, query_dict):
        logging.debug('ListView.update_with_query')
        if 'order_by' not in query_dict:
            query_dict['order_by'] = ['+timestamp']
        if query_dict['order_by'] != self._query.get('order_by'):
            property_ = query_dict['order_by'][0][1:]
            cell_text = self.sort_column.get_cells()[0]
            self.sort_column.set_attributes(cell_text,
                                            text=getattr(
                                                ListModel, 'COLUMN_' +
                                                property_.upper(),
                                                ListModel.COLUMN_TIMESTAMP))
        self._query = query_dict
        self.refresh(new_query=True)

    def refresh(self, new_query=False):
        logging.debug('ListView.refresh query %r', self._query)
        self._stop_progress_bar()

        if self._model is not None:
            if new_query:
                self._backup_selected = None
            else:
                self._backup_selected = self._model.get_selected_items()
            self._model.stop()
        self._dirty = False

        self._model = ListModel(self._query)
        self._model.connect('ready', self.__model_ready_cb)
        self._model.connect('progress', self.__model_progress_cb)
        self._model.setup()

    def __model_ready_cb(self, tree_model):
        self._stop_progress_bar()

        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__model_ready_cb %r', self._scroll_position)

        x11_window = self.tree_view.get_window()

        if x11_window is not None:
            # prevent glitches while later vadjustment setting, see #1235
            self.tree_view.get_bin_window().hide()

        # if the selection was preserved, restore it
        if self._backup_selected is not None:
            tree_model.restore_selection(self._backup_selected)
            self.emit('selection-changed', len(self._backup_selected))

        # Cannot set it up earlier because will try to access the model
        # and it needs to be ready.
        self.tree_view.set_model(self._model)

        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.tree_view.props.vadjustment.value_changed()

        if x11_window is not None:
            # prevent glitches while later vadjustment setting, see #1235
            self.tree_view.get_bin_window().show()

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
                self._show_message(_('No matching entries'),
                                   show_clear_query=True)
        else:
            self._clear_message()

    def __map_cb(self, widget):
        logging.debug('ListView.__map_cb %r', self._scroll_position)
        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.tree_view.props.vadjustment.value_changed()
        self.set_is_visible(True)

    def __unmap_cb(self, widget):
        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__unmap_cb %r', self._scroll_position)
        self.set_is_visible(False)

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
                                      icon_size=Gtk.IconSize.BUTTON)
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

    def update_dates(self):
        if not self.tree_view.get_realized():
            return
        visible_range = self.tree_view.get_visible_range()
        if visible_range is None:
            return

        logging.debug('ListView.update_dates')

        path, end_path = visible_range
        tree_model = self.tree_view.get_model()

        while True:
            cel_rect = self.tree_view.get_cell_area(path,
                                                    self.sort_column)
            x, y = self.tree_view.convert_tree_to_widget_coords(cel_rect.x,
                                                                cel_rect.y)
            self.tree_view.queue_draw_area(x, y, cel_rect.width,
                                           cel_rect.height)
            if path == end_path:
                break
            else:
                next_iter = tree_model.iter_next(tree_model.get_iter(path))
                path = tree_model.get_path(next_iter)

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
            self.refresh()

    def set_is_visible(self, visible):
        if visible != self._fully_obscured:
            return

        logging.debug('canvas_visibility_notify_event_cb %r', visible)
        if visible:
            self._fully_obscured = False
            if self._dirty:
                self.refresh()
            if self._update_dates_timer is None:
                logging.debug('Adding date updating timer')
                self._update_dates_timer = \
                    GObject.timeout_add_seconds(UPDATE_INTERVAL,
                                                self.__update_dates_timer_cb)
        else:
            self._fully_obscured = True
            if self._update_dates_timer is not None:
                logging.debug('Remove date updating timer')
                GObject.source_remove(self._update_dates_timer)
                self._update_dates_timer = None

    def __update_dates_timer_cb(self):
        self.update_dates()
        return True

    def get_model(self):
        return self._model

    def select_all(self):
        self.get_model().select_all()
        self.tree_view.queue_draw()
        self.emit('selection-changed', len(self._model.get_selected_items()))

    def select_none(self):
        self.get_model().select_none()
        self.tree_view.queue_draw()
        self.emit('selection-changed', len(self._model.get_selected_items()))


class ListView(BaseListView):
    __gtype_name__ = 'JournalListView'

    __gsignals__ = {
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([object])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
        'title-edit-started': (GObject.SignalFlags.RUN_FIRST, None,
                               ([])),
        'title-edit-finished': (GObject.SignalFlags.RUN_FIRST, None,
                                ([])),
    }

    def __init__(self, journalactivity, enable_multi_operations=False):
        BaseListView.__init__(self, journalactivity, enable_multi_operations)
        self._is_dragging = False

        self.tree_view.connect('drag-begin', self.__drag_begin_cb)
        self.tree_view.connect('button-release-event',
                               self.__button_release_event_cb)

        self.cell_title.connect('edited', self.__cell_title_edited_cb)
        self.cell_title.connect('editing-canceled', self.__editing_canceled_cb)

        self.cell_icon.connect('clicked', self.__icon_clicked_cb)
        self.cell_icon.connect('detail-clicked', self.__detail_clicked_cb)
        self.cell_icon.connect('volume-error', self.__volume_error_cb)

        cell_detail = CellRendererDetail(self.tree_view)
        cell_detail.connect('clicked', self.__detail_cell_clicked_cb)

        column = Gtk.TreeViewColumn()
        column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        column.props.fixed_width = cell_detail.props.width
        column.pack_start(cell_detail, True)
        self.tree_view.append_column(column)

    def is_dragging(self):
        return self._is_dragging

    def __drag_begin_cb(self, widget, drag_context):
        self._is_dragging = True

    def __button_release_event_cb(self, tree_view, event):
        try:
            if self._is_dragging:
                return
        finally:
            self._is_dragging = False

        pos = tree_view.get_path_at_pos(int(event.x), int(event.y))
        if pos is None:
            return

        path, column, x_, y_ = pos
        if column != self._title_column:
            return

        row = self.tree_view.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        self.cell_title.props.editable = model.is_editable(metadata)
        if self.cell_title.props.editable:
            self.emit('title-edit-started')

        tree_view.set_cursor_on_cell(path, column, self.cell_title,
                                     start_editing=True)

    def __detail_cell_clicked_cb(self, cell, path):
        row = self.tree_view.get_model()[path]
        self.emit('detail-clicked', row[ListModel.COLUMN_UID])

    def __detail_clicked_cb(self, cell, uid):
        self.emit('detail-clicked', uid)

    def __volume_error_cb(self, cell, message, severity):
        self.emit('volume-error', message, severity)

    def __icon_clicked_cb(self, cell, path):
        row = self.tree_view.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        misc.resume(metadata,
                    alert_window=journalwindow.get_journal_window())

    def __cell_title_edited_cb(self, cell, path, new_text):
        row = self._model[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        metadata['title'] = new_text
        model.write(metadata, update_mtime=False)
        self.cell_title.props.editable = False
        self.emit('title-edit-finished')

    def __editing_canceled_cb(self, cell):
        self.cell_title.props.editable = False
        self.emit('title-edit-finished')


class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererFavorite'

    def __init__(self, tree_view):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'emblem-favorite'
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE
        client = GConf.Client.get_default()
        prelit_color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.props.prelit_stroke_color = prelit_color.get_stroke_color()
        self.props.prelit_fill_color = prelit_color.get_fill_color()


class CellRendererDetail(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererDetail'

    def __init__(self, tree_view):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'go-right'
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE
        self.props.stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.prelit_stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.prelit_fill_color = style.COLOR_BLACK.get_svg()


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererActivityIcon'

    __gsignals__ = {
        'detail-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                           ([str])),
        'volume-error': (GObject.SignalFlags.RUN_FIRST, None,
                         ([str, str])),
    }

    def __init__(self, journalactivity, tree_view):
        self._journalactivity = journalactivity
        self._show_palette = True

        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        self.tree_view = tree_view

    def create_palette(self):
        if not self._show_palette:
            return None

        if self._journalactivity.get_list_view().is_dragging():
            return None

        tree_model = self.tree_view.get_model()
        metadata = tree_model.get_metadata(self.props.palette_invoker.path)

        palette = ObjectPalette(self._journalactivity, metadata, detail=True)
        palette.connect('detail-clicked',
                        self.__detail_clicked_cb)
        palette.connect('volume-error',
                        self.__volume_error_cb)
        return palette

    def __detail_clicked_cb(self, palette, uid):
        self.emit('detail-clicked', uid)

    def __volume_error_cb(self, palette, message, severity):
        self.emit('volume-error', message, severity)

    def set_show_palette(self, show_palette):
        self._show_palette = show_palette

    show_palette = GObject.property(type=bool, default=True,
                                    setter=set_show_palette)


class CellRendererBuddy(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererBuddy'

    def __init__(self, tree_view, column_index):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.STANDARD_ICON_SIZE
        self.props.height = style.STANDARD_ICON_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE

        self.tree_view = tree_view
        self._model_column_index = column_index

    def create_palette(self):
        tree_model = self.tree_view.get_model()
        row = tree_model[self.props.palette_invoker.path]

        # FIXME workaround for pygobject bug, see
        # https://bugzilla.gnome.org/show_bug.cgi?id=689277

        # if row[self._model_column_index] is not None:
        #     nick, xo_color = row[self._model_column_index]
        if row.model.do_get_value(row.iter, self._model_column_index) \
                is not None:
            nick, xo_color = row.model.do_get_value(
                row.iter, self._model_column_index)
            return BuddyPalette((nick, xo_color.to_string()))
        else:
            return None

    def set_buddy(self, buddy):
        if buddy is None:
            self.props.icon_name = None
        else:
            nick_, xo_color = buddy
            self.props.icon_name = 'computer-xo'
            self.props.xo_color = xo_color

    buddy = GObject.property(type=object, setter=set_buddy)
