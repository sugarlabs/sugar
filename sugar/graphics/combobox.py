# Copyright (C) 2007, One Laptop Per Child
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
import sys

import gobject
import gtk

class ComboBox(gtk.ComboBox):
    __gtype_name__ = 'SugarComboBox'    

    __gproperties__ = {
        'value'    : (int, None, None,
                      0, sys.maxint, 0,
                      gobject.PARAM_READABLE)
    }
    def __init__(self):
        gtk.ComboBox.__init__(self)

        self._model = gtk.ListStore(gobject.TYPE_INT,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_BOOLEAN)
        self.set_model(self._model)

        renderer = gtk.CellRendererPixbuf()
        self.pack_start(renderer, False)
        self.add_attribute(renderer, 'icon-name', 2)

        renderer = gtk.CellRendererText()
        self.pack_start(renderer, True)
        self.add_attribute(renderer, 'text', 1)

        self.set_row_separator_func(self._is_separator)
        self.connect('realize', self._realize_cb)

    def do_get_property(self, pspec):
        if pspec.name == 'value':
             action_id, text, icon_name, is_separator = self.get_active_item()
             return action_id
        else:
            return gtk.ComboBox.do_get_property(self, pspec)

    def _realize_cb(self, widget, data=None):
        if self.get_active() == -1:
            self.set_active(0)

    def append_item(self, action_id, text, icon_name=None):
        self._model.append([action_id, text, icon_name, False])

    def append_separator(self):
        self._model.append([0, None, None, True])    

    def get_active_item(self):
        index = self.get_active()
        if index == -1:
            index = 0

        row = self._model.iter_nth_child(None, index)
        return self._model[row]

    def _is_separator(self, model, row):
        action_id, text, icon_name, is_separator = model[row]
        return is_separator
