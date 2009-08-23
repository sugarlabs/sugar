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
import gconf
import pango

from sugar.graphics import style
from sugar.graphics.icon import CellRendererIcon
from sugar.graphics.xocolor import XoColor
from sugar import util

from jarabe.journal.source import Source
from jarabe.journal.listmodel import ListModel
from jarabe.journal.palettes import ObjectPalette, BuddyPalette
from jarabe.journal import model
from jarabe.journal import misc

class ListView(gtk.TreeView):
    __gtype_name__ = 'JournalListView'

    __gsignals__ = {
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([object])),
        'entry-activated': (gobject.SIGNAL_RUN_FIRST,
                            gobject.TYPE_NONE,
                            ([str])),
    }

    def __init__(self):
        gtk.TreeView.__init__(self)
        self.props.fixed_height_mode = True

        self.cell_title = None
        self.cell_icon = None
        self._title_column = None
        self.date_column = None
        self._add_columns()

        self.enable_model_drag_source(gtk.gdk.BUTTON1_MASK,
                [('text/uri-list', 0, 0), ('journal-object-id', 0, 0)],
                gtk.gdk.ACTION_COPY)

        self.cell_title.props.editable = True
        self.cell_title.connect('edited', self.__cell_title_edited_cb)

        self.cell_icon.connect('clicked', self.__icon_clicked_cb)
        self.cell_icon.connect('detail-clicked', self.__detail_clicked_cb)

        cell_detail = CellRendererDetail(self)
        cell_detail.connect('clicked', self.__detail_cell_clicked_cb)

        column = gtk.TreeViewColumn('')
        column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        column.props.fixed_width = cell_detail.props.width
        column.pack_start(cell_detail)
        self.append_column(column)

        self.connect('notify::hover-selection',
                self.__notify_hover_selection_cb)
        self.connect('button-release-event', self.__button_release_event_cb)

    def __button_release_event_cb(self, tree_view, event):
        if not tree_view.props.hover_selection:
            return False

        if event.window != tree_view.get_bin_window():
            return False

        pos = tree_view.get_path_at_pos(event.x, event.y)
        if pos is None:
            return False

        path, column_, x_, y_ = pos
        uid = tree_view.get_model()[path][Source.FIELD_UID]
        self.emit('entry-activated', uid)

        return False

    def __notify_hover_selection_cb(self, widget, pspec):
        self.cell_icon.props.show_palette = not self.props.hover_selection

    def do_size_request(self, requisition):
        # HACK: We tell the model that the view is just resizing so it can avoid
        # hitting both D-Bus and disk.
        tree_model = self.get_model()
        if tree_model is not None:
            tree_model.view_is_resizing = True
        try:
            gtk.TreeView.do_size_request(self, requisition)
        finally:
            if tree_model is not None:
                tree_model.view_is_resizing = False

    def _add_columns(self):
        cell_favorite = CellRendererFavorite(self)
        cell_favorite.connect('clicked', self.__favorite_clicked_cb)

        column = gtk.TreeViewColumn('')
        column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        column.props.fixed_width = cell_favorite.props.width
        column.pack_start(cell_favorite)
        column.set_cell_data_func(cell_favorite, self.__favorite_set_data_cb)
        self.append_column(column)

        self.cell_icon = CellRendererActivityIcon(self)

        column = gtk.TreeViewColumn('')
        column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        column.props.fixed_width = self.cell_icon.props.width
        column.pack_start(self.cell_icon)
        column.add_attribute(self.cell_icon, 'file-name', ListModel.COLUMN_ICON)
        column.add_attribute(self.cell_icon, 'xo-color',
                ListModel.COLUMN_ICON_COLOR)
        self.append_column(column)

        self.cell_title = gtk.CellRendererText()
        self.cell_title.props.ellipsize = pango.ELLIPSIZE_MIDDLE
        self.cell_title.props.ellipsize_set = True

        self._title_column = gtk.TreeViewColumn(_('Title'))
        self._title_column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        self._title_column.props.expand = True
        self._title_column.props.clickable = True
        self._title_column.pack_start(self.cell_title)
        self._title_column.add_attribute(self.cell_title, 'markup',
                                         ListModel.COLUMN_TITLE)
        self._title_column.connect('clicked', self.__header_clicked_cb)
        self.append_column(self._title_column)

        buddies_column = gtk.TreeViewColumn('')
        buddies_column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        self.append_column(buddies_column)

        for column_index in [ListModel.COLUMN_BUDDY_1, ListModel.COLUMN_BUDDY_2,
                             ListModel.COLUMN_BUDDY_3]:
            cell_icon = CellRendererBuddy(self,
                                          column_index=column_index)
            buddies_column.pack_start(cell_icon)
            buddies_column.props.fixed_width += cell_icon.props.width
            buddies_column.add_attribute(cell_icon, 'buddy', column_index)

        cell_text = gtk.CellRendererText()
        cell_text.props.xalign = 1

        # Measure the required width for a date in the form of "10 hours, 10
        # minutes ago"
        timestamp = time.time() - 10 * 60 - 10 * 60 * 60
        date = util.timestamp_to_elapsed_string(timestamp)
        date_width = self._get_width_for_string(date)

        self.date_column = gtk.TreeViewColumn(_('Date'))
        self.date_column.props.sizing = gtk.TREE_VIEW_COLUMN_FIXED
        self.date_column.props.fixed_width = date_width
        self.date_column.set_alignment(1)
        self.date_column.props.resizable = True
        self.date_column.props.clickable = True
        self.date_column.props.sort_indicator = True
        self.date_column.props.sort_order = gtk.SORT_ASCENDING
        self.date_column.pack_start(cell_text)
        self.date_column.add_attribute(cell_text, 'text', ListModel.COLUMN_DATE)
        self.date_column.connect('clicked', self.__header_clicked_cb)
        self.append_column(self.date_column)

    def __header_clicked_cb(self, column_clicked):
        if column_clicked == self._title_column:
            if self._title_column.props.sort_indicator:
                if self._title_column.props.sort_order == gtk.SORT_DESCENDING:
                    self._query['order_by'] = ['+title']
                else:
                    self._query['order_by'] = ['-title']
            else:
                self._query['order_by'] = ['+title']
        elif column_clicked == self.date_column:
            if self.date_column.props.sort_indicator:
                if self.date_column.props.sort_order == gtk.SORT_DESCENDING:
                    self._query['order_by'] = ['+timestamp']
                else:
                    self._query['order_by'] = ['-timestamp']
            else:
                self._query['order_by'] = ['+timestamp']

        self._refresh()

        # Need to update the column indicators after the model has been reset
        if self._query['order_by'] == ['-timestamp']:
            self.date_column.props.sort_indicator = True
            self._title_column.props.sort_indicator = False
            self.date_column.props.sort_order = gtk.SORT_DESCENDING
        elif self._query['order_by'] == ['+timestamp']:
            self.date_column.props.sort_indicator = True
            self._title_column.props.sort_indicator = False
            self.date_column.props.sort_order = gtk.SORT_ASCENDING
        elif self._query['order_by'] == ['-title']:
            self.date_column.props.sort_indicator = False
            self._title_column.props.sort_indicator = True
            self._title_column.props.sort_order = gtk.SORT_DESCENDING
        elif self._query['order_by'] == ['+title']:
            self.date_column.props.sort_indicator = False
            self._title_column.props.sort_indicator = True
            self._title_column.props.sort_order = gtk.SORT_ASCENDING

    def _get_width_for_string(self, text):
        # Add some extra margin
        text = text + 'aaaaa'

        widget = gtk.Label('')
        context = widget.get_pango_context()
        layout = pango.Layout(context)
        layout.set_text(text)
        width, height_ = layout.get_size()
        return pango.PIXELS(width)

    def __favorite_set_data_cb(self, column, cell, tree_model, tree_iter):
        favorite = self.get_model()[tree_iter][ListModel.COLUMN_FAVORITE]
        if favorite:
            client = gconf.client_get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            cell.props.xo_color = color
        else:
            cell.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            cell.props.fill_color = style.COLOR_WHITE.get_svg()

    def __favorite_clicked_cb(self, cell, path):
        row = self.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        if metadata['keep'] == '1':
            metadata['keep'] = '0'
        else:
            metadata['keep'] = '1'
        model.write(metadata, update_mtime=False)

    def update_dates(self):
        if not self.flags() & gtk.REALIZED:
            return

        logging.debug('ListView.update_dates')
        visible_range = self.get_visible_range()
        if visible_range is None:
            return

        path, end_path = visible_range
        while True:
            x, y, width, height = self.get_cell_area(path, self.date_column)
            x, y = self.convert_tree_to_widget_coords(x, y)
            self.queue_draw_area(x, y, width, height)
            if path == end_path:
                break
            else:
                next_iter = self.get_model().iter_next(
                        self.get_model().get_iter(path))
                path = self.get_model().get_path(next_iter)

    def __detail_cell_clicked_cb(self, cell, path):
        row = self.get_model()[path]
        self.emit('detail-clicked', row[ListModel.COLUMN_UID])

    def __detail_clicked_cb(self, cell, uid):
        self.emit('detail-clicked', uid)

    def __icon_clicked_cb(self, cell, path):
        row = self.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        misc.resume(metadata)

    def __cell_title_edited_cb(self, cell, path, new_text):
        row = self.get_model()[path]
        metadata = model.get(row[ListModel.COLUMN_UID])
        metadata['title'] = new_text
        model.write(metadata, update_mtime=False)

class CellRendererFavorite(CellRendererIcon):
    __gtype_name__ = 'JournalCellRendererFavorite'

    def __init__(self, tree_view):
        CellRendererIcon.__init__(self, tree_view)

        self.props.width = style.GRID_CELL_SIZE
        self.props.height = style.GRID_CELL_SIZE
        self.props.size = style.SMALL_ICON_SIZE
        self.props.icon_name = 'emblem-favorite'
        self.props.mode = gtk.CELL_RENDERER_MODE_ACTIVATABLE
        self.props.prelit_stroke_color = style.COLOR_BUTTON_GREY.get_svg()
        self.props.prelit_fill_color = style.COLOR_BUTTON_GREY.get_svg()

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
        'detail-clicked': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([str])),
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
        return palette

    def __detail_clicked_cb(self, palette, uid):
        self.emit('detail-clicked', uid)

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

