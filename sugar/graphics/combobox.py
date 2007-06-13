# Copyright (C) 2007, One Laptop Per Child
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
import sys
import logging

import gobject
import gtk

from sugar.graphics import units

class ComboBox(gtk.ComboBox):
    __gtype_name__ = 'SugarComboBox'    

    __gproperties__ = {
        'value'    : (int, None, None,
                      0, sys.maxint, 0,
                      gobject.PARAM_READABLE)
    }
    def __init__(self):
        gtk.ComboBox.__init__(self)

        self._text_renderer = None
        self._icon_renderer = None

        self._model = gtk.ListStore(gobject.TYPE_INT,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_STRING,
                                    gobject.TYPE_BOOLEAN)
        self.set_model(self._model)

        self.set_row_separator_func(self._is_separator)

    def do_get_property(self, pspec):
        if pspec.name == 'value':
             action_id, text, icon_name, is_separator = self.get_active_item()
             return action_id
        else:
            return gtk.ComboBox.do_get_property(self, pspec)

    def append_item(self, action_id, text, icon_name=None):
        if not self._icon_renderer and icon_name:
            self._icon_renderer = gtk.CellRendererPixbuf()
            self._icon_renderer.props.stock_size = units.microgrid_to_pixels(3)
            self.pack_start(self._icon_renderer, False)
            self.add_attribute(self._icon_renderer, 'icon-name', 2)

        if not self._text_renderer and text:
            self._text_renderer = gtk.CellRendererText()
            self.pack_end(self._text_renderer, True)
            self.add_attribute(self._text_renderer, 'text', 1)

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
