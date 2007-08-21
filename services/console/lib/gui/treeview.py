# Copyright (C) 2007, Eduardo Silva <edsiper@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import gtk

class TreeView(gtk.ScrolledWindow):
    iters = [] # Iters index

    # Create a window with a treeview object
    #
    # cols      = List of dicts, ex:
    #
    #   cols = []
    #   cols.append({'index': integer_index_position, 'name': string_col_name})
    def __init__(self, cols_def, cols_name):
        gtk.ScrolledWindow.__init__(self)

        self._iters = []
        self._treeview = gtk.TreeView()

        # Creating column data types
        self._store = gtk.TreeStore(*cols_def)

        # Columns definition
        cell = gtk.CellRendererText()
        tv_cols = []

        i=0
        for col in cols_name:
            col_tv = gtk.TreeViewColumn(col['name'], cell, text=i)
            col_tv.set_reorderable(True)
            col_tv.set_resizable(True)
            tv_cols.append(col_tv)
            i+=1

        # Setting treeview properties
        self._treeview.set_model(self._store)
        self._treeview.set_enable_search(True)
        self._treeview.set_rules_hint(True)
        
        for col in tv_cols:
            self._treeview.append_column(col)
        self.add(self._treeview)

    def add_row(self, cols_data):
        iter = self._store.insert_after(None, None)
        for col in cols_data:
            print col['index'],col['info']
            self._store.set_value(iter, int(col['index']) , col['info'])

        self.iters.append(iter)
        return iter

    def update_row(self, iter, cols_data):
        for col in cols_data:
            self._store.set_value(iter, int(col['index']) , str(col['info']))

    def remove_row(self, iter):
        self._store.remove(iter)
