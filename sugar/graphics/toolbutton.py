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
        if icon_name:
            self.set_icon(icon_name)
        self.connect('clicked', self._button_clicked_cb)

    def set_icon(self, icon_name):
        icon = Icon(icon_name=icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def get_palette(self):
        return self._palette
    
    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.invoker = WidgetInvoker(self.child)

    def set_tooltip(self, text):
        self.set_palette(Palette(text))
    
    def do_expose_event(self, event):
        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(event, self._palette)
        elif self.child.state == gtk.STATE_PRELIGHT:
            self.child.style.paint_box(event.window, gtk.STATE_PRELIGHT,
                                       gtk.SHADOW_NONE, event.area,
                                       self.child, "toolbutton-prelight",
                                       self.allocation.x,
                                       self.allocation.y,
                                       self.allocation.width,
                                       self.allocation.height)

        gtk.ToolButton.do_expose_event(self, event)
    
    def _button_clicked_cb(self, widget):
        if self._palette:
            self._palette.popdown(True)

    palette = property(get_palette, set_palette)
