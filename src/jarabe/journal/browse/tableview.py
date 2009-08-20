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
import hippo
import math
import gobject
import logging

from sugar.graphics import style
from sugar.graphics.roundbox import CanvasRoundBox

COLOR_BACKGROUND = style.COLOR_WHITE
COLOR_SELECTED = style.COLOR_TEXT_FIELD_GREY

class TableCell:
    def __init__(self):
        self.row = None

    def fillin(self):
        pass

    def on_release(self, widget, event):
        pass

class TableView(gtk.Viewport):
    def __init__(self, cell_class, rows, cols):
        gobject.GObject.__init__(self)

        self._cell_class = cell_class
        self._rows = rows
        self._cols = cols
        self._cells = []
        self._model = None
        self._hover_selection = True
        self._full_adjustment = None
        self._full_height = 0
        self._selected_cell = None

        self._table = gtk.Table()
        self._table.show()

        for y in range(self._rows + 1):
            self._cells.append(self._cols * [None])
            for x in range(self._cols):
                canvas = hippo.Canvas()
                canvas.show()
                canvas.modify_bg(gtk.STATE_NORMAL,
                        COLOR_BACKGROUND.get_gdk_color())

                sel_box = CanvasRoundBox()
                sel_box.props.border_color = COLOR_BACKGROUND.get_int()
                canvas.set_root(sel_box)
                canvas.root = sel_box

                cell = self._cell_class()
                sel_box.append(cell, hippo.PACK_EXPAND)

                if self._hover_selection:
                    canvas.connect('enter-notify-event',
                            self.__enter_notify_event_cb, cell)
                    canvas.connect('leave-notify-event',
                            self.__leave_notify_event_cb)
                canvas.connect('button-release-event',
                        self.__button_release_event_cb, cell)

                self._table.attach(canvas, x, x + 1, y, y + 1,
                        gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL, 0, 0)
                self._cells[y][x] = (canvas, cell)

        smooth_box = gtk.ScrolledWindow()
        smooth_box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        smooth_box.show()
        smooth_box.add_with_viewport(self._table)
        self.add(smooth_box)

        self.connect('key-press-event', self.__key_press_event_cb)

    def do_set_scroll_adjustments(self, hadj, vadj):
        if vadj is None:
            return
        if self._full_adjustment is not None:
            self._full_adjustment.disconnect_by_func(
                    self.__adjustment_value_changed)
        self._full_adjustment = vadj
        self._full_adjustment.connect('value-changed',
                self.__adjustment_value_changed)
        self._setup_adjustment()

    def get_size(self):
        return (self._cols, self._rows)

    def get_cursor(self):
        frame = self._get_frame()
        return (frame[0],)

    def set_cursor(self, cursor):
        if self._full_adjustment is None:
            return
        #self._full_adjustment.props.value = cursor

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
            self._model.connect('row-inserted', self.__table_resized_cb)
            self._model.connect('row-deleted', self.__table_resized_cb)
        self._setup_adjustment()

    model = gobject.property(type=object,
            getter=get_model, setter=set_model)

    def get_hover_selection(self):
        return self._hover_selection

    def set_hover_selection(self, value):
        self._hover_selection = value

    hover_selection = gobject.property(type=object,
            getter=get_hover_selection, setter=set_hover_selection)

    def get_visible_range(self):
        frame = self._get_frame()
        return ((frame[0],), (frame[1],))

    def do_size_allocate(self, alloc):
        gtk.Viewport.do_size_allocate(self, alloc)
        self._full_height = alloc.height + 100
        self._table.set_size_request(-1, self._full_height)
        self._setup_adjustment()

    def _fillin_cell(self, canvas, cell):
        if cell.row is None:
            cell.set_visible(False)
        else:
            cell.fillin()
            cell.set_visible(True)

        bg_color = COLOR_BACKGROUND
        if self._selected_cell == cell:
            if cell.get_visible():
                bg_color = COLOR_SELECTED
        canvas.root.props.background_color = bg_color.get_int()

    def _setup_adjustment(self):
        if self._full_adjustment is None or self._full_height == 0:
            return

        adj = self._full_adjustment.props

        if self._model is None:
            adj.upper = 0
            adj.value = 0
            return

        if self._cols == 0:
            adj.upper = 0
        else:
            count = self._model.iter_n_children(None)
            adj.upper = int(math.ceil(float(count) / self._cols))

        adj.value = min(adj.value, adj.upper - self._rows)
        adj.page_size = self._rows
        adj.page_increment = self._rows
        self._full_adjustment.changed()

        self.__adjustment_value_changed(self._full_adjustment)

    def _get_frame(self):
        return (int(self._full_adjustment.props.value) * self._cols,
                (int(self._full_adjustment.props.value) + self._rows) * self._cols - 1)

    def __row_changed_cb(self, model, path, iter):
        range = self._get_frame()
        if path[0] < range[0] or path[0] > range[1]:
            return

        y = (path[0] - range[0]) / self._cols
        x = (path[0] - range[0]) % self._cols

        canvas, cell = self._cells[y][x]
        cell.row = self._model.get_row(path)
        self._fillin_cell(canvas, cell)

    def __table_resized_cb(self, model=None, path=None, iter=None):
        self._setup_adjustment()

    def __key_press_event_cb(self, widget, event):
        if self._full_adjustment is None or self._full_height == 0:
            return

        adj = self._full_adjustment.props
        uplimit = adj.upper - self._rows

        if event.keyval == gtk.keysyms.Up:
            adj.value -= 1
        elif event.keyval == gtk.keysyms.Down:
            if adj.value + 1 <= uplimit:
                adj.value += 1
        elif event.keyval in (gtk.keysyms.Page_Up, gtk.keysyms.KP_Page_Up):
            adj.value -= self._rows
        elif event.keyval in (gtk.keysyms.Page_Down, gtk.keysyms.KP_Page_Down):
            if adj.value + self._rows <= uplimit:
                adj.value += self._rows
        elif event.keyval in (gtk.keysyms.Home, gtk.keysyms.KP_Home):
            adj.value = 0
        elif event.keyval in (gtk.keysyms.End, gtk.keysyms.KP_End):
            adj.value = uplimit
        else:
            return False

        return True

    def __button_release_event_cb(self, widget, event, cell):
        cell.on_release(widget, event)

    def __enter_notify_event_cb(self, canvas, event, cell):
        if cell.get_visible():
            canvas.root.props.background_color = COLOR_SELECTED.get_int()
        self._selected_cell = cell

    def __leave_notify_event_cb(self, canvas, event):
        canvas.root.props.background_color = COLOR_BACKGROUND.get_int()
        self._selected_cell = None

    def __adjustment_value_changed(self, adjustment):
        if self._model:
            count = self._model.iter_n_children(None)
        else:
            count = 0
        cell_num = int(adjustment.props.value) * self._cols

        for y in range(self._rows):
            for x in range(self._cols):
                canvas, cell = self._cells[y][x]

                cell.row = None
                if cell_num < count:
                    cell.row = self._model.get_row((cell_num,),
                            self._get_frame())

                self._fillin_cell(canvas, cell)
                cell_num += 1
