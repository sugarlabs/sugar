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
from sugar.graphics import style

_N_TABS = 8

class Toolbox(gtk.VBox):
    __gtype_name__ = 'SugarToolbox'

    __gsignals__ = {
        'current-toolbar-changed': (gobject.SIGNAL_RUN_FIRST,
                                    gobject.TYPE_NONE,
                                    ([int]))
    }

    def __init__(self):
        gtk.VBox.__init__(self)
        
        self._notebook = gtk.Notebook()
        self._notebook.set_tab_pos(gtk.POS_BOTTOM)
        self._notebook.set_show_border(False)
        self._notebook.set_show_tabs(False)
        self._notebook.props.tab_vborder = style.TOOLBOX_TAB_VBORDER
        self.pack_start(self._notebook)
        self._notebook.show()

        label = gtk.Label('')
        label.set_size_request(-1, style.TOOLBOX_SEPARATOR_HEIGHT)
        self.pack_start(label, False)
        label.show()
        
        self._notebook.connect('notify::page', self._notify_page_cb)

    def _notify_page_cb(self, notebook, pspec):
        self.emit('current-toolbar-changed', notebook.props.page)
        
    def _toolbar_box_expose_cb(self, widget, event):
        widget.style.paint_flat_box(widget.window,
                                    gtk.STATE_NORMAL, gtk.SHADOW_NONE,
                                    event.area, widget, 'toolbox',
                                    widget.allocation.x,
                                    widget.allocation.y,
                                    widget.allocation.width,
                                    widget.allocation.height)
        return False
        
    def add_toolbar(self, name, toolbar):
        label = gtk.Label(name)
        label.set_size_request(gtk.gdk.screen_width() / _N_TABS, -1)
        label.set_alignment(0.0, 0.5)

        toolbar_box = gtk.HBox()
        toolbar_box.pack_start(toolbar, True, True,
                               style.TOOLBOX_HORIZONTAL_PADDING)
        toolbar_box.connect('expose-event', self._toolbar_box_expose_cb)

        self._notebook.append_page(toolbar_box, label)
        toolbar_box.show()

        if self._notebook.get_n_pages() > 1:
            self._notebook.set_show_tabs(True)
                    
    def remove_toolbar(self, index):
        self._notebook.remove_page(index)

        if self._notebook.get_n_pages() < 2:
            self._notebook.set_show_tabs(False)

    def set_current_toolbar(self, index):
        self._notebook.set_current_page(index)
