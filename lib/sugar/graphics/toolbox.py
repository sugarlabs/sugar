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
import hippo

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics import style

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
        self._notebook.props.tab_hborder = style.TOOLBOX_TAB_HBORDER
        self.pack_start(self._notebook)
        self._notebook.show()

        # FIXME improve gtk.Notebook and do this in the theme
        self._separator = hippo.Canvas()
        box = hippo.CanvasBox(
                    border_color=style.COLOR_BUTTON_GREY.get_int(),
                    background_color=style.COLOR_PANEL_GREY.get_int(),
                    box_height=style.TOOLBOX_SEPARATOR_HEIGHT,
                    border_bottom=style.LINE_WIDTH)
        self._separator.set_root(box)
        self.pack_start(self._separator, False)
        
        self._notebook.connect('notify::page', self._notify_page_cb)

    def _notify_page_cb(self, notebook, pspec):
        self.emit('current-toolbar-changed', notebook.props.page)
        
    def add_toolbar(self, name, toolbar):
        label = gtk.Label(name)
        label.set_size_request(style.TOOLBOX_TAB_LABEL_WIDTH, -1)
        label.set_alignment(0.0, 0.5)

        event_box = gtk.EventBox()
        
        alignment = gtk.Alignment(0.0, 0.0, 1.0, 1.0)
        alignment.set_padding(0, 0, style.TOOLBOX_HORIZONTAL_PADDING,
                              style.TOOLBOX_HORIZONTAL_PADDING)

        alignment.add(toolbar)
        event_box.add(alignment)
        alignment.show()
        event_box.show()

        self._notebook.append_page(event_box, label)

        if self._notebook.get_n_pages() > 1:
            self._notebook.set_show_tabs(True)
            self._separator.show()
                    
    def remove_toolbar(self, index):
        self._notebook.remove_page(index)

        if self._notebook.get_n_pages() < 2:
            self._notebook.set_show_tabs(False)
            self._separator.hide()

    def set_current_toolbar(self, index):
        self._notebook.set_current_page(index)

    def get_current_toolbar(self):
        return self._notebook.get_current_page()
    
    current_toolbar = property(get_current_toolbar, set_current_toolbar)

