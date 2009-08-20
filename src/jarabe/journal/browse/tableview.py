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

class _SmoothTable(gtk.Bin):
    __gsignals__ = {
            'set_scroll_adjustments': (gobject.SIGNAL_RUN_LAST, None,
                                      (gtk.Adjustment, gtk.Adjustment)),
            }

    def __init__(self, cells, cell_class, rows, cols):
        self._smooth_adjustment = None
        self._smooth_window = None
        self._rows = rows
        self._heigth = 0
        self.selected_cell = None
        self.hover_selection = False

        gtk.Bin.__init__(self)

        table = gtk.Table()
        table.show()
        self.add(table)

        for y in range(rows + 1):
            cells.append(cols * [None])

            for x in range(cols):
                canvas = hippo.Canvas()
                canvas.show()
                canvas.modify_bg(gtk.STATE_NORMAL,
                        COLOR_BACKGROUND.get_gdk_color())

                sel_box = CanvasRoundBox()
                sel_box.props.border_color = COLOR_BACKGROUND.get_int()
                canvas.set_root(sel_box)
                canvas.root = sel_box

                cell = cell_class()
                sel_box.append(cell, hippo.PACK_EXPAND)

                canvas.connect('enter-notify-event',
                        self.__enter_notify_event_cb, cell)
                canvas.connect('leave-notify-event',
                        self.__leave_notify_event_cb)
                canvas.connect('button-release-event',
                        self.__button_release_event_cb, cell)

                table.attach(canvas, x, x + 1, y, y + 1,
                        gtk.EXPAND | gtk.FILL, gtk.EXPAND | gtk.FILL, 0, 0)
                cells[y][x] = (canvas, cell)

    def __button_release_event_cb(self, widget, event, cell):
        cell.on_release(widget, event)

    def __enter_notify_event_cb(self, canvas, event, cell):
        if not self.hover_selection:
            return
        if cell.get_visible():
            canvas.root.props.background_color = COLOR_SELECTED.get_int()
        self.selected_cell = cell

    def __leave_notify_event_cb(self, canvas, event):
        if not self.hover_selection:
            return
        canvas.root.props.background_color = COLOR_BACKGROUND.get_int()
        self.selected_cell = None

    def do_size_allocate(self, allocation):
        self.allocation = allocation
        self._heigth = int(math.ceil(float(allocation.height) / self._rows))

        if self.flags() & gtk.REALIZED:
            self.window.move_resize(*allocation)
            self._smooth_window.resize(allocation.width,
                    allocation.height + self._heigth)

        self._set_adjustment_upper()
        self._smooth_adjustment.changed()

        table_allocation = allocation.copy()
        table_allocation.height += self._heigth
        self.child.size_allocate(table_allocation)

    def do_size_request(self, requisition):
        requisition.width, requisition.height = self.child.size_request()

    def do_realize(self):
        gtk.Bin.do_realize(self)

        self.window = gtk.gdk.Window(self.get_parent_window(),
                window_type=gtk.gdk.WINDOW_CHILD,
                x=self.allocation.x,
                y=self.allocation.y,
                width=self.allocation.width,
                height=self.allocation.height,
                wclass=gtk.gdk.INPUT_OUTPUT,
                colormap=self.get_colormap(),
                event_mask=gtk.gdk.VISIBILITY_NOTIFY_MASK)

        self.window.set_user_data(self)
        self.set_style(self.style.attach(self.window))
        self.style.set_background(self.window, gtk.STATE_NORMAL)

        self._smooth_window = gtk.gdk.Window(self.window,
                window_type=gtk.gdk.WINDOW_CHILD,
                x=0,
                y=int(-self._smooth_adjustment.value),
                width=self.allocation.width,
                height=self.allocation.height + self._heigth,
                colormap=self.get_colormap(),
                wclass=gtk.gdk.INPUT_OUTPUT,
                event_mask=(self.get_events() | gtk.gdk.EXPOSURE_MASK | \
                        gtk.gdk.SCROLL_MASK))

        self._smooth_window.set_user_data(self)
        self.style.set_background(self._smooth_window, gtk.STATE_NORMAL)
        self.child.set_parent_window(self._smooth_window)

        self.queue_resize()

    def do_unrealize(self):
        self._smooth_window.set_user_data(None)
        self._smooth_window.destroy()
        self._smooth_window = None
        gtk.Bin.do_unrealize(self)

    def do_map(self):
        gtk.Bin.do_map(self)
        self._smooth_window.show()
        self.window.show()

    def do_set_scroll_adjustments(self, hadjustment, vadjustment):
        if vadjustment is None or vadjustment == self._smooth_adjustment:
            return

        if self._smooth_adjustment is not None:
            self._smooth_adjustment.disconnect_by_func(self.__value_changed_cb)

        self._smooth_adjustment = vadjustment
        self._set_adjustment_upper()
        vadjustment.connect('value-changed', self.__value_changed_cb)
        self.__value_changed_cb()

    def __value_changed_cb(self, sender=None):
        if not self.flags() & gtk.REALIZED:
            return
        self._smooth_window.move(0, int(-self._smooth_adjustment.value))
        self.window.process_updates(True)

    def _set_adjustment_upper(self):
        adj = self._smooth_adjustment
        adj.page_size = 0
        adj.page_increment = 0
        adj.lower = 0

        if self._heigth != adj.upper:
            adj.upper = self._heigth
            adj.changed()

        if adj.value > adj.upper:
            adj.value = adj.upper
            adj.value_changed()

class TableView(gtk.Bin):
    __gsignals__ = {
            'set_scroll_adjustments': (gobject.SIGNAL_RUN_LAST, None,
                                      (gtk.Adjustment, gtk.Adjustment)),
            }

    def __init__(self, cell_class, rows, cols):
        self._rows = rows
        self._cols = cols
        self._cells = []
        self._model = None
        self._full_adjustment = None
        self._cell_height = 0
        self._top_cell = None
        self._last_adjustment = -1

        gtk.Bin.__init__(self)

        self._table = _SmoothTable(self._cells, cell_class, rows, cols)
        self._table.show()

        smooth_box = gtk.ScrolledWindow()
        smooth_box.set_policy(gtk.POLICY_NEVER, gtk.POLICY_NEVER)
        smooth_box.show()
        smooth_box.add(self._table)
        self.add(smooth_box)

        self.connect('key-press-event', self.__key_press_event_cb)

    def get_size(self):
        return (self._cols, self._rows)

    def get_cursor(self):
        frame = self._get_frame()
        return (frame[0],)

    def set_cursor(self, cursor):
        if self._full_adjustment is None or self._cell_height == 0:
            return
        self._full_adjustment.props.value = self._cell_height * cursor
        self._full_adjustment.changed()

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
        return self._table.hover_selection

    def set_hover_selection(self, value):
        self._table.hover_selection = value

    hover_selection = gobject.property(type=object,
            getter=get_hover_selection, setter=set_hover_selection)

    def get_visible_range(self):
        frame = self._get_frame()
        return ((frame[0],), (frame[1],))

    def do_set_scroll_adjustments(self, hadjustment, vadjustment):
        if vadjustment is None or vadjustment == self._full_adjustment:
            return
        if self._full_adjustment is not None:
            self._full_adjustment.disconnect_by_func(
                    self.__adjustment_value_changed)
        self._full_adjustment = vadjustment
        self._full_adjustment.connect('value-changed',
                self.__adjustment_value_changed)
        self._setup_adjustment()

    def do_size_allocate(self, allocation):
        self.child.size_allocate(allocation)
        self._cell_height = allocation.height / self._rows
        self._setup_adjustment()

    def do_size_request(self, requisition):
        requisition.width, requisition.height = self.child.size_request()

    def _fillin_cell(self, canvas, cell):
        if self._table.selected_cell == cell and cell.get_visible():
            bg_color = COLOR_SELECTED
        else:
            bg_color = COLOR_BACKGROUND
        canvas.root.props.background_color = bg_color.get_int()

        if cell.row is None:
            cell.set_visible(False)
        else:
            cell.fillin()
            cell.set_visible(True)

        canvas.root.props.background_color = bg_color.get_int()

    def _setup_adjustment(self):
        if self._full_adjustment is None or self._cell_height == 0:
            return

        adj = self._full_adjustment

        if self._model is None:
            adj.upper = 0
            adj.value = 0
            return

        count = self._model.iter_n_children(None)

        adj.upper = max(0, math.ceil(float(count) / self._cols) * \
                self._cell_height)
        adj.value = min(adj.value, adj.upper)
        adj.page_size = self._cell_height * self._rows
        adj.page_increment = adj.page_size
        self._full_adjustment.changed()

        self.__adjustment_value_changed(self._full_adjustment, force=True)

    def _get_frame(self):
        adj = self._full_adjustment
        return (int(adj.value / self._cell_height) * self._cols,
               (int(adj.value / self._cell_height) + self._rows) * \
                       self._cols - 1)

    def __adjustment_value_changed(self, adjustment, force=False):
        if self._last_adjustment == int(adjustment.value):
            return
        self._last_adjustment = int(adjustment.value)

        cell_row = int(adjustment.props.value) / self._cell_height
        cell_num = cell_row * self._cols

        smooth_adj = self.child.props.vadjustment
        smooth_adj_value = int(min(smooth_adj.upper,
                int(adjustment.props.value) - (cell_row * self._cell_height)))

        if cell_num == self._top_cell and not force:
            smooth_adj.value = smooth_adj_value
            smooth_adj.value_changed()
            return
        self._top_cell = cell_num

        if self._model is not None:
            count = self._model.iter_n_children(None)
        else:
            count = 0

        for y in range(self._rows + 1):
            for x in range(self._cols):
                canvas, cell = self._cells[y][x]

                cell.row = None
                if cell_num < count:
                    cell.row = self._model.get_row((cell_num,),
                            self._get_frame())

                self._fillin_cell(canvas, cell)
                cell_num += 1

        smooth_adj.value = smooth_adj_value
        smooth_adj.value_changed()

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
        if self._full_adjustment is None or self._cell_height == 0:
            return

        adj = self._full_adjustment.props
        page = self._rows * self._cell_height
        uplimit = adj.upper - page

        if event.keyval == gtk.keysyms.Up:
            adj.value -= self._cell_height

        elif event.keyval == gtk.keysyms.Down:
            adj.value += min(uplimit - adj.value, self._cell_height)

        elif event.keyval in (gtk.keysyms.Page_Up, gtk.keysyms.KP_Page_Up):
            adj.value -= min(adj.value, page)

        elif event.keyval in (gtk.keysyms.Page_Down, gtk.keysyms.KP_Page_Down):
            adj.value += min(uplimit - adj.value, page)

        elif event.keyval in (gtk.keysyms.Home, gtk.keysyms.KP_Home):
            adj.value = 0

        elif event.keyval in (gtk.keysyms.End, gtk.keysyms.KP_End):
            adj.value = uplimit

        else:
            return False

        return True

TableView.set_set_scroll_adjustments_signal('set-scroll-adjustments')
_SmoothTable.set_set_scroll_adjustments_signal('set-scroll-adjustments')
