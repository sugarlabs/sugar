# Copyright (C) 2007, Red Hat, Inc.
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
import gobject

from sugar.graphics.toolbutton import ToolButton

_N_TABS = 8

class Toolbox(gtk.VBox):
    __gtype_name__ = 'SugarToolbox'
    def __init__(self):
        gtk.VBox.__init__(self)
        
        self._notebook = gtk.Notebook()
        self._notebook.set_name('sugar-toolbox-notebook')
        self._notebook.set_tab_pos(gtk.POS_BOTTOM)
        self._notebook.set_show_border(False)
        self.pack_start(self._notebook)
        self._notebook.show()
        
    def add_toolbar(self, name, toolbar):
        label = gtk.Label(name)
        label.set_size_request(gtk.gdk.screen_width() / _N_TABS, -1)
        label.set_alignment(0.0, 0.5)
        self._notebook.append_page(toolbar, label)
        
    def remove_toolbar(self, index):
        self._notebook.remove_page(index)
