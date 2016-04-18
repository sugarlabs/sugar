# Copyright (C) 2016, Abhijit Patel
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

from gi.repository import GObject
from gi.repository import Gtk

from sugar3.graphics import style
from sugar3.graphics.icon import CellRendererIcon

from jarabe.view.friendlistmodel import FriendListModel


class FriendListView(Gtk.TreeView):
    __gtype_name__ = 'FriendListView'

    def __init__(self):
        Gtk.TreeView.__init__(self)

        self._model = FriendListModel()
        self.set_model(self._model.get_liststore())
        selection = self.get_selection()
        selection.set_mode(Gtk.SelectionMode.NONE)

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
        self.append_column(column)

        buddies_column = Gtk.TreeViewColumn()
        buddies_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self.append_column(buddies_column)

        cell_icon = CellRendererBuddy()
        cell_icon.props.sensitive = False
        buddies_column.pack_start(cell_icon, True)
        buddies_column.props.fixed_width += cell_icon.props.width
        buddies_column.add_attribute(cell_icon,
                                     'xo-color',
                                     FriendListModel.COLUMN_XO_COLOR)
        buddies_column.set_cell_data_func(cell_icon,
                                          self.__buddies_set_data_cb)
        self.append_column(buddies_column)

        self.cell_title = Gtk.CellRendererText()
        self.cell_title.props.ellipsize = style.ELLIPSIZE_MODE_DEFAULT
        self.cell_title.props.ellipsize_set = True

        self._title_column = Gtk.TreeViewColumn()
        self._title_column.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self._title_column.props.expand = True
        self._title_column.props.clickable = False
        self._title_column.pack_start(self.cell_title, True)
        self._title_column.add_attribute(self.cell_title, 'markup',
                                         FriendListModel.COLUMN_NICK)
        self.append_column(self._title_column)

    def get_model(self):
        return self._model

    def __select_set_data_cb(self, column, cell, tree_model, tree_iter,
                             data):
        logging.debug('select_set_data_cb')
        friend = tree_model[tree_iter]

        if friend is None:
            return
        cell.props.active = \
            self._model.is_selected(friend[FriendListModel.COLUMN_FRIEND])

    def __cell_select_toggled_cb(self, cell, path):
        logging.debug('cell_select_toggled_cb')
        friend = self._model.get_liststore()[path]
        if friend is None:
            return
        self._model.set_selected(friend[FriendListModel.COLUMN_FRIEND],
                                 not cell.get_active())
        cell.props.active =  \
            self._model.is_selected(friend[FriendListModel.COLUMN_FRIEND])

    def __buddies_set_data_cb(self, column, cell, tree_model, tree_iter,
                              data):
        friend = tree_model[tree_iter]
        cell.props.xo_color = friend[FriendListModel.COLUMN_XO_COLOR]


class CellRendererBuddy(CellRendererIcon):
    __gtype_name__ = 'CellRendererBuddy'

    def __init__(self):
        CellRendererIcon.__init__(self)

        self.props.width = style.STANDARD_ICON_SIZE
        self.props.height = style.STANDARD_ICON_SIZE
        self.props.size = style.STANDARD_ICON_SIZE
        self.props.mode = Gtk.CellRendererMode.ACTIVATABLE
        self.props.icon_name = 'computer-xo'
        self.nick = None

    def set_buddy(self, buddy):
        if buddy is None:
            self.props.icon_name = None
            self.nick = None
        else:
            self.nick, xo_color = buddy
            self.props.xo_color = xo_color

    buddy = GObject.property(type=object, setter=set_buddy)
