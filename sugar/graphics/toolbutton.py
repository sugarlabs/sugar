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
    def __init__(self, named_icon=None):
        gtk.ToolButton.__init__(self)
        self.set_named_icon(named_icon)
        
    def set_named_icon(self, named_icon):
        icon = Icon(named_icon)
        self.set_icon_widget(icon)
        icon.show()

    def set_palette(self, palette):
        self.connect('clicked', palette.display)
        palette.props.parent = self
        palette.props.alignment = ALIGNMENT_BOTTOM_LEFT

    def set_tooltip(self, text):
        tp = gtk.Tooltips()
        self.set_tooltip(tp, text, text)
