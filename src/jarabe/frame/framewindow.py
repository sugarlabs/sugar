# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
from gtk import gdk
import gobject

from sugar.graphics import style


class FrameContainer(gtk.Bin):
    """A container class for frame panel rendering. Hosts a child 'box' where
    frame elements can be added. Excludes grid-sized squares at each end
    of the frame panel, and a space alongside the inside of the screen where
    a border is drawn."""

    __gtype_name__ = 'SugarFrameContainer'

    def __init__(self, position):
        gtk.Bin.__init__(self)
        self._position = position

        if self.is_vertical():
            box = gtk.VBox()
        else:
            box = gtk.HBox()
        self.add(box)
        box.show()

    def is_vertical(self):
        return self._position in (gtk.POS_LEFT, gtk.POS_RIGHT)

    def do_expose_event(self, event):
        # Draw the inner border as a rectangle
        cr = self.get_parent_window().cairo_create()
        r, g, b, a = style.COLOR_BUTTON_GREY.get_rgba()
        cr.set_source_rgba (r, g, b, a)

        if self.is_vertical():
            x = style.GRID_CELL_SIZE if self._position == gtk.POS_LEFT else 0
            y = style.GRID_CELL_SIZE
            width = style.LINE_WIDTH
            height = self.allocation.height - (style.GRID_CELL_SIZE * 2)
        else:
            x = style.GRID_CELL_SIZE
            y = style.GRID_CELL_SIZE if self._position == gtk.POS_TOP else 0
            height = style.LINE_WIDTH
            width = self.allocation.width - (style.GRID_CELL_SIZE * 2)

        cr.rectangle(x, y, width, height)
        cr.fill()

        gtk.Bin.do_expose_event(self, event)
        return False

    def do_size_request(self, req):
        if self.is_vertical():
            req.height = gdk.screen_height()
            req.width = style.GRID_CELL_SIZE + style.LINE_WIDTH
        else:
            req.width = gdk.screen_width()
            req.height = style.GRID_CELL_SIZE + style.LINE_WIDTH

        self.get_child().size_request()

    def do_size_allocate(self, allocation):
        self.allocation = allocation

        # exclude grid squares at two ends of the frame
        # allocate remaining space to child box, minus the space needed for
        # drawing the border
        allocation = gdk.Rectangle()
        if self.is_vertical():
            allocation.x = 0 if self._position == gtk.POS_LEFT \
                else style.LINE_WIDTH
            allocation.y = style.GRID_CELL_SIZE
            allocation.width = self.allocation.width - style.LINE_WIDTH
            allocation.height = self.allocation.height \
                - (style.GRID_CELL_SIZE * 2)
        else:
            allocation.x = style.GRID_CELL_SIZE
            allocation.y = 0 if self._position == gtk.POS_TOP \
                else style.LINE_WIDTH
            allocation.width = self.allocation.width \
                - (style.GRID_CELL_SIZE * 2)
            allocation.height = self.allocation.height - style.LINE_WIDTH

        self.get_child().size_allocate(allocation)


class FrameWindow(gtk.Window):
    __gtype_name__ = 'SugarFrameWindow'

    def __init__(self, position):
        gtk.Window.__init__(self)
        self.hover = False
        self.size = style.GRID_CELL_SIZE + style.LINE_WIDTH

        accel_group = gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self._position = position

        self.set_decorated(False)
        self.connect('realize', self._realize_cb)
        self.connect('enter-notify-event', self._enter_notify_cb)
        self.connect('leave-notify-event', self._leave_notify_cb)

        self._container = FrameContainer(position)
        self.add(self._container)
        self._container.show()
        self._update_size()

        screen = gdk.screen_get_default()
        screen.connect('size-changed', self._size_changed_cb)

    def append(self, child, expand=True, fill=True):
        self._container.get_child().pack_start(child, expand=expand, fill=fill)

    def _update_size(self):
        if self._position == gtk.POS_TOP or self._position == gtk.POS_BOTTOM:
            self.resize(gdk.screen_width(), self.size)
        else:
            self.resize(self.size, gdk.screen_height())

    def _realize_cb(self, widget):
        self.window.set_type_hint(gdk.WINDOW_TYPE_HINT_DOCK)
        self.window.set_accept_focus(False)

    def _enter_notify_cb(self, window, event):
        if event.detail != gdk.NOTIFY_INFERIOR:
            self.hover = True

    def _leave_notify_cb(self, window, event):
        if event.detail != gdk.NOTIFY_INFERIOR:
            self.hover = False

    def _size_changed_cb(self, screen):
        self._update_size()
