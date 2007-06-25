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
from sugar.graphics.palette import *

class ToolButton(gtk.ToolButton):
    _POPUP_PALETTE_DELAY = 100

    def __init__(self, icon_name=None):
        gtk.ToolButton.__init__(self)
        self._palette = None
        self.set_icon(icon_name)
        self.child.connect('enter-notify-event',self._enter_notify_event_cb)
        self.child.connect('leave-notify-event',self._leave_notify_event_cb)
        self._enter_tag = None
        self._leave_tag = None

    def set_icon(self, icon_name):
        icon = Icon(icon_name)
        self.set_icon_widget(icon)
        icon.show()

    def set_palette(self, palette):
        self._palette = palette
        self._palette.props.invoker = WidgetInvoker(self)

    def set_tooltip(self, text):
        if self._palette:
            self._palette.destroy()

        self._palette = Palette()
        self._palette.set_primary_state(text)
        self._palette.props.invoker = WidgetInvoker(self)

    def _enter_notify_event_cb(self, widget, event):
        if not self._palette:
            return

        gtk.gdk.pointer_ungrab()

        if self._leave_tag:
            gobject.source_remove(self._leave_tag)
            self._leave_tag = None

        self._enter_tag = gobject.timeout_add(self._POPUP_PALETTE_DELAY, \
            self._show_palette)

    def _leave_notify_event_cb(self, widget, event):
        if not self._palette:
            return

        if self._enter_tag:
            gobject.source_remove(self._enter_tag)
            self._enter_tag = None

        self._leave_tag = gobject.timeout_add(self._POPUP_PALETTE_DELAY,\
            self._hide_palette)

    def _show_palette(self):
        self._palette.popup()
        return False

    def _hide_palette(self):
        # Just hide the palette if the mouse pointer is 
        # out of the toolbutton and the palette
        if self._is_mouse_out(self._palette):
            self._palette.popdown()
        else:
            gtk.gdk.pointer_ungrab()
        
        return False

    def _pointer_grab(self):
        gtk.gdk.pointer_grab(self.window, owner_events=True,\
            event_mask=gtk.gdk.PROPERTY_CHANGE_MASK )

    def _is_mouse_out(self, widget):
        mouse_x, mouse_y = widget.get_pointer()
        event_rect = gdk.Rectangle(mouse_x, mouse_y, 1, 1)

        if (widget.allocation.intersect(event_rect).width==0):
            return True
        else:
            return False
