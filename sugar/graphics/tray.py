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

from sugar.graphics import style
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.icon import Icon

_PREVIOUS_PAGE = 0
_NEXT_PAGE = 1

class _TrayViewport(gtk.Viewport):
    __gproperties__ = {
        'can-scroll' : (bool, None, None, False,
                        gobject.PARAM_READABLE),
    }

    def __init__(self, orientation):
        self.orientation = orientation
        self._can_scroll = False

        gobject.GObject.__init__(self)

        self.set_shadow_type(gtk.SHADOW_NONE)

        self.traybar = gtk.Toolbar()
        self.traybar.set_orientation(orientation)
        self.traybar.set_show_arrow(False)
        self.add(self.traybar)
        self.traybar.show()

        self.connect('size_allocate', self._size_allocate_cb)

    def scroll(self, direction):
        if direction == _PREVIOUS_PAGE:
            self._scroll_previous()
        elif direction == _NEXT_PAGE:
            self._scroll_next()

    def _scroll_next(self):
        if self.orientation == gtk.ORIENTATION_HORIZONTAL:
            adj = self.get_hadjustment()
            new_value = adj.value + self.allocation.width
            adj.value = min(new_value, adj.upper - self.allocation.width)
        else:
            adj = self.get_vadjustment()
            new_value = adj.value + self.allocation.height
            adj.value = min(new_value, adj.upper - self.allocation.height)

    def _scroll_previous(self):
        if self.orientation == gtk.ORIENTATION_HORIZONTAL:
            adj = self.get_hadjustment()
            new_value = adj.value - self.allocation.width
            adj.value = max(adj.lower, new_value)
        else:
            adj = self.get_vadjustment()
            new_value = adj.value - self.allocation.height
            adj.value = max(adj.lower, new_value)

    def do_size_request(self, requisition):
        child_requisition = self.child.size_request()
        if self.orientation == gtk.ORIENTATION_HORIZONTAL:
            requisition[0] = 0
            requisition[1] = child_requisition[1]
        else:
            requisition[0] = child_requisition[0]
            requisition[1] = 0

    def do_get_property(self, pspec):
        if pspec.name == 'can-scroll':
            return self._can_scroll

    def _size_allocate_cb(self, viewport, allocation):
        bar_requisition = self.traybar.get_child_requisition()
        if self.orientation == gtk.ORIENTATION_HORIZONTAL:
            can_scroll = bar_requisition[0] > allocation.width
        else:
            can_scroll = bar_requisition[1] > allocation.height

        if can_scroll != self._can_scroll:
            self._can_scroll = can_scroll
            self.notify('can-scroll')

class _TrayScrollButton(gtk.Button):
    def __init__(self, icon_name, scroll_direction):
        gobject.GObject.__init__(self)

        self._viewport = None

        self._scroll_direction = scroll_direction

        self.set_relief(gtk.RELIEF_NONE)
        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

        icon = Icon(icon_name = icon_name,
                    icon_size=gtk.ICON_SIZE_SMALL_TOOLBAR)
        self.set_image(icon)
        icon.show()

        self.connect('clicked', self._clicked_cb)

    def set_viewport(self, viewport):
        self._viewport = viewport
        self._viewport.connect('notify::can-scroll',
                               self._viewport_can_scroll_changed_cb)

    def _viewport_can_scroll_changed_cb(self, viewport, pspec):
        self.props.visible = self._viewport.props.can_scroll

    def _clicked_cb(self, button):
        self._viewport.scroll(self._scroll_direction)

    viewport = property(fset=set_viewport)

class HTray(gtk.HBox):
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, **kwargs)

        scroll_left = _TrayScrollButton('go-left', _PREVIOUS_PAGE)
        self.pack_start(scroll_left, False)

        self._viewport = _TrayViewport(gtk.ORIENTATION_HORIZONTAL)
        self.pack_start(self._viewport)
        self._viewport.show()

        scroll_right = _TrayScrollButton('go-right', _NEXT_PAGE)
        self.pack_start(scroll_right, False)

        scroll_left.viewport = self._viewport
        scroll_right.viewport = self._viewport

    def add_item(self, item, index=-1):
        self._viewport.traybar.insert(item, index)

    def remove_item(self, item):
        self._viewport.traybar.remove(item)

    def get_item_index(self, item):
        return self._viewport.traybar.get_item_index(item)

class VTray(gtk.VBox):
    def __init__(self, **kwargs):
        gobject.GObject.__init__(self, **kwargs)

        # FIXME we need a go-up icon
        scroll_left = _TrayScrollButton('go-left', _PREVIOUS_PAGE)
        self.pack_start(scroll_left, False)

        self._viewport = _TrayViewport(gtk.ORIENTATION_VERTICAL)
        self.pack_start(self._viewport)
        self._viewport.show()

        # FIXME we need a go-down icon
        scroll_right = _TrayScrollButton('go-right', _NEXT_PAGE)
        self.pack_start(scroll_right, False)

        scroll_left.viewport = self._viewport
        scroll_right.viewport = self._viewport

    def add_item(self, item, index=-1):
        self._viewport.traybar.insert(item, index)

    def remove_item(self, item):
        self._viewport.traybar.remove(item)

    def get_item_index(self, item):
        return self._viewport.traybar.get_item_index(item)

class TrayButton(ToolButton):
    def __init__(self, **kwargs):
        ToolButton.__init__(self, **kwargs)
