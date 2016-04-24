# Copyright (C) 2011-2012 One Laptop Per Child
# Copyright (C) 2010 Tomeu Vizoso
# Copyright (C) 2011 Walter Bender
# Copyright (C) 2011 Raul Gutierrez Segales
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


class ViewContainer(Gtk.Container):
    __gtype_name__ = 'SugarViewContainer'

    def __init__(self, layout, owner_icon, activity_icon=None, **kwargs):
        Gtk.Container.__init__(self, **kwargs)
        self.set_has_window(False)
        self.set_can_focus(True)

        self._activity_icon = None
        self._owner_icon = None
        self._layout = None

        self._children = []
        self.set_layout(layout)

        if owner_icon:
            self._owner_icon = owner_icon
            self.add(self._owner_icon)
            self._owner_icon.show()

        if activity_icon:
            self._activity_icon = activity_icon
            self.add(self._activity_icon)
            self._activity_icon.show()

    def do_add(self, child):
        if child != self._owner_icon and child != self._activity_icon:
            self._children.append(child)
        if child.get_realized():
            child.set_parent_window(self.get_parent_window())
        child.set_parent(self)

    def do_remove(self, child):
        was_visible = child.get_visible()
        if child in self._children:
            self._children.remove(child)
            child.unparent()
            self._layout.remove(child)
            if was_visible and self.get_visible():
                self.queue_resize()

    def do_size_allocate(self, allocation):
        self.set_allocation(allocation)
        if self._owner_icon:
            self._layout.setup(allocation, self._owner_icon,
                               self._activity_icon)

        self._layout.allocate_children(allocation, self._children)

    def do_forall(self, include_internals, callback):
        for child in self._children:
            callback(child)
        if self._owner_icon:
            callback(self._owner_icon)
        if self._activity_icon:
            callback(self._activity_icon)

    def set_layout(self, layout):
        for child in self.get_children():
            self.remove(child)
        self._layout = layout
