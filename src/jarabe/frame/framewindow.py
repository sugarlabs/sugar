# Copyright (C) 2006-2007 Red Hat, Inc.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics import style


class FrameContainer(Gtk.Bin):
    """A container class for frame panel rendering. Hosts a child 'box' where
    frame elements can be added. Excludes grid-sized squares at each end
    of the frame panel, and a space alongside the inside of the screen where
    a border is drawn."""

    __gtype_name__ = 'SugarFrameContainer'

    def __init__(self, position):
        Gtk.Bin.__init__(self)
        self._position = position

        if self.is_vertical():
            box = Gtk.VBox()
        else:
            box = Gtk.HBox()
        self.add(box)
        box.show()

    def is_vertical(self):
        return self._position in (Gtk.PositionType.LEFT,
                                  Gtk.PositionType.RIGHT)

    def do_draw(self, cr):
        # Draw the inner border as a rectangle
        r, g, b, a = style.COLOR_BUTTON_GREY.get_rgba()
        cr.set_source_rgba(r, g, b, a)

        allocation = self.get_allocation()
        if self.is_vertical():
            x = style.GRID_CELL_SIZE \
                if self._position == Gtk.PositionType.LEFT else 0
            y = style.GRID_CELL_SIZE
            width = style.LINE_WIDTH
            height = allocation.height - (style.GRID_CELL_SIZE * 2)
        else:
            x = style.GRID_CELL_SIZE
            y = style.GRID_CELL_SIZE \
                if self._position == Gtk.PositionType.TOP else 0
            height = style.LINE_WIDTH
            width = allocation.width - (style.GRID_CELL_SIZE * 2)

        cr.rectangle(x, y, width, height)
        cr.fill()

        Gtk.Bin.do_draw(self, cr)
        return False

    def do_size_request(self, req):
        if self.is_vertical():
            req.height = Gdk.Screen.height()
            req.width = style.GRID_CELL_SIZE + style.LINE_WIDTH
        else:
            req.width = Gdk.Screen.width()
            req.height = style.GRID_CELL_SIZE + style.LINE_WIDTH

        self.get_child().size_request()

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)

        # exclude grid squares at two ends of the frame
        # allocate remaining space to child box, minus the space needed for
        # drawing the border
        allocation = Gdk.Rectangle()
        if self.is_vertical():
            allocation.x = 0 if self._position == Gtk.PositionType.LEFT \
                else style.LINE_WIDTH
            allocation.y = style.GRID_CELL_SIZE
            allocation.width = self.get_allocation().width - style.LINE_WIDTH
            allocation.height = self.get_allocation().height \
                - (style.GRID_CELL_SIZE * 2)
        else:
            allocation.x = style.GRID_CELL_SIZE
            allocation.y = 0 if self._position == Gtk.PositionType.TOP \
                else style.LINE_WIDTH
            allocation.width = self.get_allocation().width \
                - (style.GRID_CELL_SIZE * 2)
            allocation.height = self.get_allocation().height - style.LINE_WIDTH

        self.get_child().size_allocate(allocation)


class FrameWindow(Gtk.Window):
    __gtype_name__ = 'SugarFrameWindow'

    def __init__(self, position):
        Gtk.Window.__init__(self)
        self.set_has_resize_grip(False)
        self.hover = False
        self.size = style.GRID_CELL_SIZE + style.LINE_WIDTH

        accel_group = Gtk.AccelGroup()
        self.sugar_accel_group = accel_group
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

        screen = Gdk.Screen.get_default()
        screen.connect('size-changed', self._size_changed_cb)

    def append(self, child, expand=True, fill=True):
        self._container.get_child().pack_start(child, expand=expand, fill=fill,
                                               padding=0)

    def _update_size(self):
        if self._position == Gtk.PositionType.TOP \
                or self._position == Gtk.PositionType.BOTTOM:
            self.resize(Gdk.Screen.width(), self.size)
        else:
            self.resize(self.size, Gdk.Screen.height())

    def _realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DOCK)
        self.get_window().set_accept_focus(False)

    def _enter_notify_cb(self, window, event):
        if event.detail != Gdk.NotifyType.INFERIOR:
            self.hover = True

    def _leave_notify_cb(self, window, event):
        if event.detail != Gdk.NotifyType.INFERIOR:
            self.hover = False

    def _size_changed_cb(self, screen):
        self._update_size()
if hasattr(FrameWindow, 'set_css_name'):
    FrameWindow.set_css_name('framewindow')
