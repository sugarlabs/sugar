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

from sugar.graphics.icon import Icon
from sugar.graphics.palette import *

class ToolButton(gtk.ToolButton):
    def __init__(self, icon_name=None):
        gtk.ToolButton.__init__(self)
        self.set_icon(icon_name)
        
    def set_icon(self, icon_name):
        icon = Icon(icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.parent = self
        self._palette.props.alignment = ALIGNMENT_BOTTOM_LEFT
        self.connect('clicked', self._display_palette_cb)
    
    def set_tooltip(self, text):
        tp = gtk.Tooltips()
        self.set_tooltip(tp, text, text)

    def _display_palette_cb(self, widget):
        self._palette.popup()
