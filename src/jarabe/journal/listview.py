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

import gobject
import gtk
import hippo
import gconf
import pango

from sugar.graphics import style
from sugar.graphics.icon import CanvasIcon, Icon, CellRendererIcon
from sugar.graphics.xocolor import XoColor
from sugar import util

from jarabe.journal.listmodel import ListModel
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import model
from jarabe.journal import misc


UPDATE_INTERVAL = 300


class TreeView(gtk.TreeView):
    __gtype_name__ = 'JournalTreeView'

    def __init__(self):
        gtk.TreeView.__init__(self)
        self.set_headers_visible(False)
        self.set_enable_search(False)

    def do_size_request(self, requisition):
        # HACK: We tell the model that the view is just resizing so it can
        # avoid hitting both D-Bus and disk.
        tree_model = self.get_model()
        if tree_model is not None:
            tree_model.view_is_resizing = True
        try:
            gtk.TreeView.do_size_request(self, requisition)
        finally:
            if tree_model is not None:
                tree_model.view_is_resizing = False


class BaseListView(gtk.Bin):
    __gtype_name__ = 'JournalBaseListView'

    __gsignals__ = {
        'clear-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE, ([])),
    }

    def __init__(self):
        self._query = {}
        self._model = None
        self._progress_bar = None
        self._last_progress_bar_pulse = None
        self._scroll_position = 0.

        gobject.GObject.__init__(self)

        self.connect('map', self.__map_cb)
        self.connect('unrealize', self.__unrealize_cb)
        self.connect('destroy', self.__destroy_cb)

        self._scrolled_window = gtk.ScrolledWindow()
        self._scrolled_window.set_policy(gtk.POLICY_NEVER,
                                         gtk.POLICY_AUTOMATIC)
        self.add(self._scrolled_window)
        self._scrolled_window.show()

        self.tree_view = TreeView()
        selection = self.tree_view.get_selection()
        selection.set_mode(gtk.SELECTION_NONE)
        self.tree_view.props.fixed_height_mode = True
        self.tree_view.modify_base(gtk.STATE_NORMAL,
                                   style.COLOR_WHITE.get_gdk_color())
        self._scrolled_window.add(self.tree_view)
        self.tree_view.show()

        self.cell_title = None
        self.cell_icon = None
        self._title_column = None
        self.sort_column = None
        self._add_columns()

        self.tree_view.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                                                [('text/uri-list', 0, 0),
                                                 ('journal-object-id', 0, 0)],
                                                gtk.gdk.ACTION_COPY)

        # Auto-update stuff
        self._fully_obscured = True
        self._dirty = False
        self._refresh_idle_handler = None
        self._update_dates_timer = None

        model.created.connect(self.__model_created_cb)
        model.updated.connect(self.__model_updated_cb)
        model.deleted.connect(self.__model_deleted_cb)

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
        cell_favorite = CellRendererFavorite(self.tree_view)
        cell_favorite.connect('clicked', self.__favorite_clicked_cb)

        column = gtk.TreeViewColumn()
        column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        column.props.fixed_width = cell_favorite.props.width
        column.pack_start(cell_favorite)
        column.set_cell_data_func(cell_favorite, self.__favorite_set_data_cb)
        self.tree_view.append_column(column)

        self.cell_icon = CellRendererActivityIcon(self.tree_view)

        column = gtk.TreeViewColumn()
        column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        column.props.fixed_width = self.cell_icon.props.width
        column.pack_start(self.cell_icon)
        column.add_attribute(self.cell_icon, 'file-name',
                             ListModel.COLUMN_ICON)
        column.add_attribute(self.cell_icon, 'xo-color',
                             ListModel.COLUMN_ICON_COLOR)
        self.tree_view.append_column(column)

        self.cell_title = gtk.CellRendererText()
        self.cell_title.props.ellipsize = pango.ELLIPSIZE_MIDDLE
        self.cell_title.props.ellipsize_set = True

        self._title_column = gtk.TreeViewColumn()
        self._title_column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        self._title_column.props.expand = True
        self._title_column.props.clickable = True
        self._title_column.pack_start(self.cell_title)
        self._title_column.add_attribute(self.cell_title, 'markup',
                                         ListModel.COLUMN_TITLE)
        self.tree_view.append_column(self._title_column)

        buddies_column = gtk.TreeViewColumn()
        buddies_column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        self.tree_view.append_column(buddies_column)

        for column_index in [ListModel.COLUMN_BUDDY_1,
                             ListModel.COLUMN_BUDDY_2,
                             ListModel.COLUMN_BUDDY_3]:
            cell_icon = CellRendererBuddy(self.tree_view,
                                          column_index=column_index)
            buddies_column.pack_start(cell_icon)
            buddies_column.props.fixed_width += cell_icon.props.width
            buddies_column.add_attribute(cell_icon, 'buddy', column_index)
            buddies_column.set_cell_data_func(cell_icon,
                    self.__buddies_set_data_cb)

        cell_progress = gtk.CellRendererProgress()
        cell_progress.props.ypad = style.GRID_CELL_SIZE / 4
        buddies_column.pack_start(cell_progress)
        buddies_column.add_attribute(cell_progress, 'value',
                ListModel.COLUMN_PROGRESS)
        buddies_column.set_cell_data_func(cell_progress,
                self.__progress_data_cb)

        cell_text = gtk.CellRendererText()
        cell_text.props.xalign = 1

        # Measure the required width for a date in the form of "10 hours, 10
        # minutes ago"
        timestamp = time.time() - 10 * 60 - 10 * 60 * 60
        date = util.timestamp_to_elapsed_string(timestamp)
        date_width = self._get_width_for_string(date)

        self.sort_column = gtk.TreeViewColumn()
        self.sort_column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        self.sort_column.props.fixed_width = date_width
        self.sort_column.set_alignment(1)
        self.sort_column.props.resizable = True
        self.sort_column.props.clickable = True
        self.sort_column.pack_start(cell_text)
        self.sort_column.add_attribute(cell_text, 'text',
                                       ListModel.COLUMN_TIMESTAMP)
        self.tree_view.append_column(self.sort_column)

    def _get_width_for_string(self, text):
        # Add some extra margin
        text = text + 'aaaaa'

        widget = gtk.Label('')
        context = widget.get_pango_context()
        layout = pango.Layout(context)
        layout.set_text(text)
        width, height_ = layout.get_size()
        return pango.PIXELS(width)

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        self.child.size_allocate(allocation)

    def do_size_request(self, requisition):
        requisition.width, requisition.height = self.child.size_request()

    def __destroy_cb(self, widget):
        if self._model is not None:
            self._model.stop()

    def __buddies_set_data_cb(self, column, cell, tree_model, tree_iter):
        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        cell.props.visible = progress >= 100

    def __progress_data_cb(self, column, cell, tree_model, tree_iter):
        progress = tree_model[tree_iter][ListModel.COLUMN_PROGRESS]
        cell.props.visible = progress < 100

    def __favorite_set_data_cb(self, column, cell, tree_model, tree_iter):
        favorite = tree_model[tree_iter][ListModel.COLUMN_FAVORITE]
        if favorite:
            client = gconf.client_get_default()
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

    def update_with_query(self, query_dict):
        logging.debug('ListView.update_with_query')
        if 'order_by' not in query_dict:
            query_dict['order_by'] = ['+timestamp']
        if query_dict['order_by'] != self._query.get('order_by'):
            property_ = query_dict['order_by'][0][1:]
            cell_text = self.sort_column.get_cell_renderers()[0]
            self.sort_column.set_attributes(cell_text,
                text=getattr(ListModel, 'COLUMN_' + property_.upper(),
                             ListModel.COLUMN_TIMESTAMP))
        self._query = query_dict

        self.refresh()

    def refresh(self):
        logging.debug('ListView.refresh query %r', self._query)
        self._stop_progress_bar()

        if self._model is not None:
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

        if self.tree_view.window is not None:
            # prevent glitches while later vadjustment setting, see #1235
            self.tree_view.get_bin_window().hide()

        # Cannot set it up earlier because will try to access the model
        # and it needs to be ready.
        self.tree_view.set_model(self._model)

        self.tree_view.props.vadjustment.props.value = self._scroll_position
        self.tree_view.props.vadjustment.value_changed()

        if self.tree_view.window is not None:
            # prevent glitches while later vadjustment setting, see #1235
            self.tree_view.get_bin_window().show()

        if len(tree_model) == 0:
            if self._is_query_empty():
                if self._query['mountpoints'] == ['/']:
                    self._show_message(_('Your Journal is empty'))
                elif self._query['mountpoints'] == \
                        [model.get_documents_path()]:
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

    def __unrealize_cb(self, widget):
        self._scroll_position = self.tree_view.props.vadjustment.props.value
        logging.debug('ListView.__map_cb %r', self._scroll_position)

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
        alignment = gtk.Alignment(xalign=0.5, yalign=0.5, xscale=0.5)
        self.remove(self.child)
        self.add(alignment)
        alignment.show()

        self._progress_bar = gtk.ProgressBar()
        self._progress_bar.props.pulse_step = 0.01
        self._last_progress_bar_pulse = time.time()
        alignment.add(self._progress_bar)
        self._progress_bar.show()

    def _stop_progress_bar(self):
        if self._progress_bar is None:
            return
        self.remove(self.child)
        self.add(self._scrolled_window)
        self._progress_bar = None

    def _show_message(self, message, show_clear_query=False):
        canvas = hippo.Canvas()
        self.remove(self.child)
        self.add(canvas)
        canvas.show()

        box = hippo.CanvasBox(orientation=hippo.ORIENTATION_VERTICAL,
                              background_color=style.COLOR_WHITE.get_int(),
                              yalign=hippo.ALIGNMENT_CENTER,
                              spacing=style.DEFAULT_SPACING,
                              padding_bottom=style.GRID_CELL_SIZE)
        canvas.set_root(box)

        icon = CanvasIcon(size=style.LARGE_ICON_SIZE,
                          icon_name='activity-journal',
                          stroke_color=style.COLOR_BUTTON_GREY.get_svg(),
                          fill_color=style.COLOR_TRANSPARENT.get_svg())
        box.append(icon)

        text = hippo.CanvasText(text=message,
                xalign=hippo.ALIGNMENT_CENTER,
                font_desc=style.FONT_BOLD.get_pango_desc(),
                color=style.COLOR_BUTTON_GREY.get_int())
        box.append(text)

        if show_clear_query:
            button = gtk.Button(label=_('Clear search'))
            button.connect('clicked', self.__clear_button_clicked_cb)
            button.props.image = Icon(icon_name='dialog-cancel',
                                      icon_size=gtk.ICON_SIZE_BUTTON)
            canvas_button = hippo.CanvasWidget(widget=button,
                                               xalign=hippo.ALIGNMENT_CENTER)
            box.append(canvas_button)

    def __clear_button_clicked_cb(self, button):
        self.emit('clear-clicked')

    def _clear_message(self):
        if self.child == self._scrolled_window:
            return
        self.remove(self.child)
        self.add(self._scrolled_window)
        self._scrolled_window.show()

    def update_dates(self):
        if not self.tree_view.flags() & gtk.REALIZED:
            return
        visible_range = self.tree_view.get_visible_range()
        if visible_range is None:
            return

        logging.debug('ListView.update_dates')

        path, end_path = visible_range
        tree_model = self.tree_view.get_model()

        while True:
            x, y, width, height = self.tree_view.get_cell_area(path,
                self.sort_column)
            x, y = self.tree_view.convert_tree_to_widget_coords(x, y)
            self.tree_view.queue_draw_area(x, y, width, height)
            if path == end_path:
                break
            else:
                next_iter = tree_model.iter_next(tree_model.get_iter(path))
                path = tree_model.get_path(next_iter)

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
            if self._update_dates_timer is None:
                logging.debug('Adding date updating timer')
                self._update_dates_timer = \
                        gobject.timeout_add_seconds(UPDATE_INTERVAL,
                                            self.__update_dates_timer_cb)
        else:
            self._fully_obscured = True
            if self._update_dates_timer is not None:
                logging.debug('Remove date updating timer')
                gobject.source_remove(self._update_dates_timer)
                self._update_dates_timer = None

    def __update_dates_timer_cb(self):
        self.update_dates()
        return True


class ListView(BaseListView):
    __gtype_name__ = 'JournalListView'

    __gsignals__ = {
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([object])),
        'volume-error': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                         ([str, str])),
    }

    def __init__(self):
        BaseListView.__init__(self)
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

        column = gtk.TreeViewColumn()
        column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        column.props.fixed_width = cell_detail.props.width
        column.pack_start(cell_detail)
        self.tree_view.append_column(column)

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

        tree_view.set_cursor_on_cell(path, column, start_editing=True)

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
        misc.resume(metadata)

    def __cell_title_edited_cb(self, cell, path, new_text):
        row = self._model[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        metadata['title'] = new_text
        model.write(metadata, update_mtime=False)
        self.cell_title.props.editable = False

    def __editing_canceled_cb(self, cell):
        self.cell_title.props.editable = False


class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererFavorite'

    def __init__(self, tree_view):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'emblem-favorite'
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE
        client = gconf.client_get_default()
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
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE
        self.props.stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.prelit_stroke_color = style.COLOR_TRANSPARENT.get_svg()
        self.props.prelit_fill_color = style.COLOR_BLACK.get_svg()


class CellRendererActivityIcon(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererActivityIcon'

    __gsignals__ = {
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([str])),
        'volume-error': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                           ([str, str])),
    }

    def __init__(self, tree_view):
        self._show_palette = True

        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE

        self.tree_view = tree_view

    def create_palette(self):
        if not self._show_palette:
            return None

        tree_model = self.tree_view.get_model()
        metadata = tree_model.get_metadata(self.props.palette_invoker.path)

        palette = ObjectPalette(metadata, detail=True)
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

    show_palette = gobject.property(type=bool, default=True,
                                    setter=set_show_palette)


class CellRendererBuddy(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererBuddy'

    def __init__(self, tree_view, column_index):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.STANDARD_ICON_SIZE
        self.props.height = style.STANDARD_ICON_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE

        self.tree_view = tree_view
        self._model_column_index = column_index

    def create_palette(self):
        tree_model = self.tree_view.get_model()
        row = tree_model[self.props.palette_invoker.path]

        if row[self._model_column_index] is not None:
            nick, xo_color = row[self._model_column_index]
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

    buddy = gobject.property(type=object, setter=set_buddy)
