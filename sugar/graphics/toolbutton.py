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
import time

from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette, WidgetInvoker

class ToolButton(gtk.ToolButton):
    __gtype_name__ = "SugarToolButton"

    def __init__(self, icon_name=None):
        gtk.ToolButton.__init__(self)
        self._palette = None
        self.set_icon(icon_name)
        self.connect('clicked', self._button_clicked_cb)

    def set_icon(self, icon_name):
        icon = Icon(icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def get_palette(self):
        return self._palette
    
    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.invoker = WidgetInvoker(self.child)
        self._palette.props.draw_gap = True
        
        self._palette.connect("popup", self._palette_changed)
        self._palette.connect("popdown", self._palette_changed)

    def set_tooltip(self, text):
        self.set_palette(Palette(text))
    
    def do_expose_event(self, event):
        if self._palette:
            if self._palette.is_up() or self.child.state == gtk.STATE_PRELIGHT:
                invoker = self._palette.props.invoker
                invoker.draw_invoker_rect(event, self._palette)

        gtk.ToolButton.do_expose_event(self, event)
    
    def _button_clicked_cb(self, widget):
        if self._palette:
            self._palette.popdown(True)

    def _palette_changed(self, palette):
        # Force a redraw to update the invoker rectangle
        self.queue_draw()

    palette = property(get_palette, set_palette)
