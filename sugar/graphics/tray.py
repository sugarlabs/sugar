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

import gobject
import gtk

from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.icon import Icon

class _TrayViewport(gtk.Viewport):
    __gproperties__ = {
        'can-scroll' : (bool, None, None, False,
                        gobject.PARAM_READABLE),
    }

    def __init__(self):
        self._can_scroll = False

        gobject.GObject.__init__(self)

        self.set_shadow_type(gtk.SHADOW_NONE)

        self.traybar = gtk.Toolbar()
        self.traybar.set_show_arrow(False)
        self.add(self.traybar)
        self.traybar.show()

        self.connect('size_allocate', self._size_allocate_cb)

    def scroll_right(self):
        adj = self.get_hadjustment()
        new_value = adj.value + self.allocation.width
        adj.value = min(new_value, adj.upper - self.allocation.width)

    def scroll_left(self):
        adj = self.get_hadjustment()
        new_value = adj.value - self.allocation.width
        adj.value = max(adj.lower, new_value)

    def do_get_property(self, pspec):
        if pspec.name == 'can-scroll':
            return self._can_scroll

    def _size_allocate_cb(self, viewport, allocation):
        bar_requisition = self.traybar.get_child_requisition()
        if bar_requisition[0] < allocation.width:
            can_scroll = False
        else:
            can_scroll = True

        if can_scroll != self._can_scroll:
            self._can_scroll = can_scroll
            self.notify('can-scroll')

class HTray(gtk.HBox):
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, **kwargs)

        self._scroll_left = gtk.Button()
        self._scroll_left.set_relief(gtk.RELIEF_NONE)
        self._scroll_left.connect('clicked', self._scroll_left_cb)

        icon = Icon(icon_name='go-left', icon_size=gtk.ICON_SIZE_MENU)
        self._scroll_left.set_image(icon)
        icon.show()

        self.pack_start(self._scroll_left, False)

        self._viewport = _TrayViewport()
        self._viewport.connect('notify::can-scroll',
                               self._viewport_can_scroll_changed_cb)
        self.pack_start(self._viewport)
        self._viewport.show()

        self._scroll_right = gtk.Button()
        self._scroll_right.set_relief(gtk.RELIEF_NONE)
        self._scroll_right.connect('clicked', self._scroll_right_cb)

        icon = Icon(icon_name='go-right', icon_size=gtk.ICON_SIZE_MENU)
        self._scroll_right.set_image(icon)
        icon.show()

        self.pack_start(self._scroll_right, False)

    def _viewport_can_scroll_changed_cb(self, viewport, pspec):
        if self._viewport.props.can_scroll:
            self._scroll_left.show()
            self._scroll_right.show()

    def _scroll_left_cb(self, button):
        self._viewport.scroll_left()

    def _scroll_right_cb(self, button):
        self._viewport.scroll_right()

    def add_item(self, item, index=-1):
        self._viewport.traybar.insert(item, index)

    def remove_item(self, index):
        item = self._viewport.traybar.get_nth_item(index)
        self._viewport.traybar.remove(item)

    def get_item_index(self, item):
        return self._viewport.traybar.get_item_index(item)

class TrayButton(ToolButton):
    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)
