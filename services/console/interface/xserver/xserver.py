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

import gobject
from pyxres import XRes
from ui.treeview import TreeView

class XorgView(TreeView):
    def __init__(self):
        col_names = []
        col_names.append({'index': 0, 'name': 'PID'})
        col_names.append({'index': 1, 'name': 'Resource Base'})
        col_names.append({'index': 2, 'name': 'Pixmap Bytes'})
        col_names.append({'index': 3, 'name': 'Other'})
        col_names.append({'index': 4, 'name': 'Total'})
        col_names.append({'index': 5, 'name': 'Window Name'})

        self._window_iter = []

        cols_type = [str, str, str, str, str, str]
        TreeView.__init__(self, cols_type, col_names)

        self._xres = XRes()
        self._display = self._xres.open_display()
        self.show_all()
        gobject.timeout_add(1500, self._update_data)

    def _nice_bytes(self, bytes):
        prefix = "B"
        value = bytes

        if bytes/1024:
            prefix = "K"
            value = (bytes/1024)

        return "%s%s" % (value, prefix)

    def _update_data(self):
        windows = self._xres.get_windows(self._display)
        print windows
        for w in windows:
            row = []
            row.append({'index':0, 'info': w.pid})

            bytes = self._nice_bytes(w.pixmap_bytes)
            obytes = self._nice_bytes(w.other_bytes)
            tbytes = self._nice_bytes(w.pixmap_bytes+w.other_bytes)
            
            row.append({'index':1, 'info': hex(w.resource_base)})
            row.append({'index':2, 'info': bytes})
            row.append({'index':3, 'info': obytes})
            row.append({'index':4, 'info': tbytes})
            row.append({'index':5, 'info': w.wm_name})

            iter = self._get_window_iter(w.pid)
            if not iter:
                iter = self.add_row(row)
                self._set_window_iter(iter, w.pid)
            else:
                self.update_row(iter, row)

        self._clear_down_windows(windows)
        return True

    def _set_window_iter(self, iter, pid):
        self._window_iter.append([iter, pid])

    def _remove_iface_iter(self, search_iter):
        i = 0
        for [iter, pid] in self._window_iter:
            if iter == search_iter:
                del self._window_iter[i]
                return
            i+=1

    def _get_window_iter(self, wpid):
        for [iter, pid] in self._window_iter:
            if wpid == pid:
                return iter

        return None

    def _clear_down_windows(self, windows):
        for [iter, pid] in self._window_iter:
            found = False
            for w in windows:
                if w.pid == pid:
                    found = True
                    break

            if not found:
                self.remove_row(iter)
                self._remove_window_iter(iter)

class Interface(object):
    def __init__(self):
        self.widget = XorgView()
