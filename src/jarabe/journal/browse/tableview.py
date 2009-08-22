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
import math
import hippo
import gobject
import logging

from sugar.graphics import style
from sugar.graphics.roundbox import CanvasRoundBox
from jarabe.journal.browse.smoothtable import SmoothTable

COLOR_BACKGROUND = style.COLOR_WHITE
COLOR_SELECTED = style.COLOR_TEXT_FIELD_GREY

class TableCell:
    def __init__(self):
        self.row = None
        self.tree = None

    def do_fill_in(self):
        pass

class TableView(SmoothTable):
    def __init__(self, cell_class, rows, columns):
        SmoothTable.__init__(self, rows, columns,
                lambda: self._create_cell(cell_class), self._fill_in)

        self._model = None
        self._hover_selection = False
        self._selected_cell = None

    def get_cursor(self):
        return (self.frame[0],)

    def set_cursor(self, cursor):
        self.goto(cursor)

    def get_model(self):
        return self._model

    def set_model(self, model):
        if self._model == model:
            return

        if self._model:
            self._model.disconnect_by_func(self.__row_changed_cb)
            self._model.disconnect_by_func(self.__table_resized_cb)

        self._model = model

        if model:
            self._model.connect('row-changed', self.__row_changed_cb)
            self._model.connect('rows-reordered', self.__table_resized_cb)

        self._resize()

    model = gobject.property(type=object,
            getter=get_model, setter=set_model)

    def get_hover_selection(self):
        return self._hover_selection

    def set_hover_selection(self, value):
        self._hover_selection = value

    hover_selection = gobject.property(type=object,
            getter=get_hover_selection, setter=set_hover_selection)

    def get_visible_range(self):
        return ((self.frame[0],), (self.frame[1],))

    def _create_cell(self, cell_class):
        canvas = hippo.Canvas()
        canvas.show()
        canvas.modify_bg(gtk.STATE_NORMAL, COLOR_BACKGROUND.get_gdk_color())

        sel_box = CanvasRoundBox()
        sel_box.props.border_color = COLOR_BACKGROUND.get_int()
        canvas.set_root(sel_box)

        cell = cell_class()
        cell.tree = self
        sel_box.append(cell, hippo.PACK_EXPAND)

        canvas.connect('enter-notify-event', self.__enter_notify_event_cb, cell)
        canvas.connect('leave-notify-event', self.__leave_notify_event_cb)

        canvas.table_view_cell_sel_box = sel_box
        canvas.table_view_cell = cell

        return canvas

    def _resize(self):
        rows = int(math.ceil(float(self._model.iter_n_children(None)) / \
                self.columns))
        self.bin_rows = rows

    def _fill_in(self, canvas, y, x, prepared_row=None):

        cell = canvas.table_view_cell
        sel_box = canvas.table_view_cell_sel_box

        if self._selected_cell == cell and cell.get_visible():
            bg_color = COLOR_SELECTED
        else:
            bg_color = COLOR_BACKGROUND
        sel_box.props.background_color = bg_color.get_int()

        cell.row = prepared_row

        if cell.row is None:
            cell_num = y * self.columns + x

            if cell_num < self._model.iter_n_children(None):
                row = self._model.get_row((cell_num,), self.frame)
                if row != False:
                    cell.row = row

        if cell.row is None:
            cell.set_visible(False)
        else:
            cell.do_fill_in()
            cell.set_visible(True)

    def __enter_notify_event_cb(self, canvas, event, cell):
        if not self.hover_selection:
            return

        if cell.get_visible():
            sel_box = canvas.table_view_cell_sel_box
            sel_box.props.background_color = COLOR_SELECTED.get_int()

        self._selected_cell = cell

    def __leave_notify_event_cb(self, canvas, event):
        if not self.hover_selection:
            return

        sel_box = canvas.table_view_cell_sel_box
        sel_box.props.background_color = COLOR_BACKGROUND.get_int()

        self._selected_cell = None

    def __row_changed_cb(self, model, path, iter):
        y = path[0] / self.columns
        x = path[0] % self.columns

        canvas = self.get_visible_cell(y, x)
        if canvas is None:
            return

        row = self._model.get_row(path)
        self._fill_in(canvas, y, x, row)

    def __table_resized_cb(self, model=None, path=None, iter=None, arg3=None):
        self._resize()
