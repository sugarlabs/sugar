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
import gobject
import logging

from sugar.graphics.palette import Invoker

_SHOW_PALETTE_TIMEOUT = 200


class TreeView(gtk.TreeView):

    def __init__(self):
        gtk.TreeView.__init__(self)
        self._invoker = _TreeInvoker(self)

    def set_cursor(self, path, column, edit=False):
        if path is not None:
            gtk.TreeView.set_cursor(self, path, column, edit)

    def append_column(self, column):
        if isinstance(column, TreeViewColumn):
            column.view = self
        return gtk.TreeView.append_column(self, column)

    def create_palette(self):
        return self._invoker.cell_palette


class TreeViewColumn(gtk.TreeViewColumn):

    def __init__(self, title=None, cell=None, **kwargs):
        gtk.TreeViewColumn.__init__(self, title, cell, **kwargs)
        self.view = None
        self._order_by = None
        self.palette_cb = None
        self.connect('clicked', self._clicked_cb)

    def set_sort_column_id(self, field):
        self.props.clickable = True
        self._order_by = field

    def get_sort_column_id(self):
        return self._order_by

    def _clicked_cb(self, column):
        if self.view is None:
            return

        if self.props.sort_indicator:
            if self.props.sort_order == gtk.SORT_DESCENDING:
                new_order = gtk.SORT_ASCENDING
            else:
                new_order = gtk.SORT_DESCENDING
        else:
            new_order = gtk.SORT_ASCENDING

        self.view.get_model().set_order(self._order_by, new_order)


class _TreeInvoker(Invoker):

    def __init__(self, tree=None):
        Invoker.__init__(self)
        self._position_hint = self.AT_CURSOR

        self._tree = None
        self.cell_palette = None
        self._palette_pos = None
        self._enter_timeout = None

        self._enter_hid = None
        self._motion_hid = None
        self._leave_hid = None
        self._button_hid = None

        if tree is not None:
            self.attach(tree)

    def get_toplevel(self):
        return self._tree.get_toplevel()

    def attach(self, tree):
        self._tree = tree
        self._enter_hid = tree.connect('enter-notify-event', self._enter_cb)
        self._motion_hid = tree.connect('motion-notify-event', self._enter_cb)
        self._leave_hid = tree.connect('leave-notify-event', self._leave_cb)
        self._button_hid = tree.connect('button-release-event',
                self._button_cb)
        Invoker.attach(self, tree)

    def detach(self):
        Invoker.detach(self)
        self._tree.disconnect(self._enter_hid)
        self._tree.disconnect(self._motion_hid)
        self._tree.disconnect(self._leave_hid)
        self._tree.disconnect(self._button_cb)

    def _close_palette(self):
        if self._enter_timeout:
            gobject.source_remove(self._enter_timeout)
            self._enter_timeout = None
        self.cell_palette = None
        self._palette_pos = None

    def _open_palette(self, notify, force):
        if self._enter_timeout:
            gobject.source_remove(self._enter_timeout)
            self._enter_timeout = None

        coords = self._tree.convert_widget_to_bin_window_coords(
                *self._tree.get_pointer())

        pos = self._tree.get_path_at_pos(*coords)
        if not pos:
            self._close_palette()
            return False

        path, column, x, y = pos
        if not hasattr(column, 'palette_cb') or not column.palette_cb:
            self._close_palette()
            return False

        row = self._tree.props.model.get_row(path)
        if row is None:
            logging.debug('_open_palette: wait for row %s' % path)
            self._enter_timeout = gobject.timeout_add(500, self._open_palette,
                    self.notify_mouse_enter, False)
            return False

        palette = column.palette_cb(self._tree.props.model, row, x, y)
        if palette is None:
            self._close_palette()
            return False

        if self._palette_pos != (path, column) or self.cell_palette != palette:
            if self.palette is not None:
                self.palette.popdown(True)
                self.palette = None

        self._palette_pos = (path, column)
        self.cell_palette = palette
        notify()

        return False

    def notify_popup(self):
        Invoker.notify_popup(self)

    def notify_popdown(self):
        Invoker.notify_popdown(self)

    def _enter_cb(self, widget, event):
        if self._enter_timeout:
            gobject.source_remove(self._enter_timeout)
        self._enter_timeout = gobject.timeout_add(_SHOW_PALETTE_TIMEOUT,
                self._open_palette, self.notify_mouse_enter, False)

    def _leave_cb(self, widget, event):
        self.notify_mouse_leave()
        self._close_palette()

    def _button_cb(self, widget, event):
        if event.button == 3:
            return self._open_palette(self.notify_right_click, True)
        else:
            return False
