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
import time

from sugar.graphics.icon import Icon
from sugar.graphics.palette import *

class ToolButton(gtk.ToolButton):
    _POPUP_PALETTE_DELAY = 0.15

    def __init__(self, icon_name=None):
        gtk.ToolButton.__init__(self)
        self._palette = None
        self.set_icon(icon_name)

    def set_icon(self, icon_name):
        icon = Icon(icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.parent = self
        self.child.connect('enter-notify-event', self._show_palette_timeout_cb)

    def set_tooltip(self, text):
        if self._palette:
            self._palette.destroy()

        self._palette = Palette(is_tooltip=True)
        self._palette.set_primary_state(text)
        self._palette.props.parent = self
        self.child.connect('enter-notify-event', self._show_palette_timeout_cb)

    def _show_palette_timeout_cb(self, widget, event):
        time.sleep(self._POPUP_PALETTE_DELAY)
        self._palette.popup()
