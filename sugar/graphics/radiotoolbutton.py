# Copyright (C) 2007, Red Hat, Inc.
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

import gtk

from sugar.graphics.icon import Icon
from sugar.graphics.palette import Palette, ToolInvoker

class RadioToolButton(gtk.RadioToolButton):
    __gtype_name__ = "SugarRadioToolButton"

    def __init__(self, named_icon=None, group=None, xo_color=None):
        gtk.RadioToolButton.__init__(self, group=group)
        self._palette = None
        self._xo_color = xo_color
        self.set_named_icon(named_icon)

    def set_named_icon(self, named_icon):
        icon = Icon(icon_name=named_icon,
                    xo_color=self._xo_color,
                    icon_size=gtk.ICON_SIZE_LARGE_TOOLBAR)
        self.set_icon_widget(icon)
        icon.show()

    def get_palette(self):
        return self._palette
    
    def set_palette(self, palette):
        if self._palette is not None:        
            self._palette.props.invoker = None
        self._palette = palette
        self._palette.props.invoker = ToolInvoker(self)

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

        gtk.RadioToolButton.do_expose_event(self, event)
    
    palette = property(get_palette, set_palette)
