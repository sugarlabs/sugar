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
from sugar.graphics.palette import Palette, WidgetInvoker

class RadioToolButton(gtk.RadioToolButton):
    __gtype_name__ = "SugarRadioToolButton"

    def __init__(self, named_icon=None, group=None):
        gtk.RadioToolButton.__init__(self, group=group)
        self._palette = None
        self.set_named_icon(named_icon)

    def set_named_icon(self, named_icon):
        icon = Icon(named_icon)
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
        self._palette = Palette(text)
        self._palette.props.invoker = WidgetInvoker(self.child)

    def do_expose_event(self, event):
        if self._palette:
            if self._palette.is_up() or self.child.state == gtk.STATE_PRELIGHT:
                invoker = self._palette.props.invoker
                invoker.draw_invoker_rect(event, self._palette)

        gtk.RadioToolButton.do_expose_event(self, event)
    
    def _palette_changed(self, palette):
        # Force a redraw to update the invoker rectangle
        self.queue_draw()
    
    palette = property(get_palette, set_palette)
