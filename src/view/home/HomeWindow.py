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

# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk

from sugar.graphics import style
from sugar.graphics import palettegroup

from view.home.MeshBox import MeshBox
from view.home.HomeBox import HomeBox
from view.home.FriendsBox import FriendsBox
from view.home.transitionbox import TransitionBox
from model.shellmodel import ShellModel
from model import shellmodel

_HOME_PAGE       = 0
_FRIENDS_PAGE    = 1
_MESH_PAGE       = 2
_TRANSITION_PAGE = 3

class HomeWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)

        accel_group = gtk.AccelGroup()
        self.set_data('sugar-accel-group', accel_group)
        self.add_accel_group(accel_group)

        self._active = False
        self._level = ShellModel.ZOOM_HOME

        self.set_default_size(gtk.gdk.screen_width(),
                              gtk.gdk.screen_height())

        self.realize()
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
        self.connect('visibility-notify-event',
                     self._visibility_notify_event_cb)

        self._enter_sid = self.connect('enter-notify-event',
                                       self._enter_notify_event_cb)
        self._leave_sid = self.connect('leave-notify-event',
                                       self._leave_notify_event_cb)
        self._motion_sid = self.connect('motion-notify-event',
                                        self._motion_notify_event_cb)

        self._home_box = HomeBox()
        self._friends_box = FriendsBox()
        self._mesh_box = MeshBox()
        self._transition_box = TransitionBox()

        self._activate_view()
        self.add(self._home_box)
        self._home_box.show()

        self._transition_box.connect('completed',
                                     self._transition_completed_cb)

        model = shellmodel.get_instance()
        model.connect('notify::zoom-level', self.__zoom_level_changed_cb)

    def _enter_notify_event_cb(self, window, event):
        if event.x != gtk.gdk.screen_width() / 2 or \
           event.y != gtk.gdk.screen_height() / 2:
            self._mouse_moved()

    def _leave_notify_event_cb(self, window, event):
        self._mouse_moved()

    def _motion_notify_event_cb(self, window, event):
        self._mouse_moved()

    # We want to enable the XO palette only when the user
    # moved away from the default mouse position (screen center).
    def _mouse_moved(self):
        self._home_box.enable_xo_palette()
        self.disconnect(self._leave_sid)
        self.disconnect(self._motion_sid)
        self.disconnect(self._enter_sid)

    def _deactivate_view(self):
        group = palettegroup.get_group("default")
        group.popdown()
        if self._level == ShellModel.ZOOM_HOME:
            self._home_box.suspend()
        elif self._level == ShellModel.ZOOM_MESH:
            self._mesh_box.suspend()

    def _activate_view(self):
        if self._level == ShellModel.ZOOM_HOME:
            self._home_box.resume()
        elif self._level == ShellModel.ZOOM_MESH:
            self._mesh_box.resume()

    def _visibility_notify_event_cb(self, window, event):
        if event.state == gtk.gdk.VISIBILITY_FULLY_OBSCURED:
            self._deactivate_view()
        else:
            self._activate_view()

    def __zoom_level_changed_cb(self, model, pspec):
        level = model.props.zoom_level
        if level == ShellModel.ZOOM_ACTIVITY:
            return

        self._deactivate_view()
        self._level = level
        self._activate_view()

        self.remove(self.get_child())    
        self.add(self._transition_box)
        self._transition_box.show()

        if self._level == ShellModel.ZOOM_HOME:
            size = style.XLARGE_ICON_SIZE
        elif self._level == ShellModel.ZOOM_FRIENDS:
            size = style.LARGE_ICON_SIZE
        elif self._level == ShellModel.ZOOM_MESH:
            size = style.STANDARD_ICON_SIZE
            
        self._transition_box.set_size(size)
    
    def _transition_completed_cb(self, transition_box):
        current_child = self.get_child()
        self.remove(current_child)

        if self._level == ShellModel.ZOOM_HOME:
            self.add(self._home_box)
            self._home_box.show()
        elif self._level == ShellModel.ZOOM_FRIENDS:
            self.add(self._friends_box)
            self._friends_box.show()
        elif self._level == ShellModel.ZOOM_MESH:
            self.add(self._mesh_box)
            self._mesh_box.show()
            self._mesh_box.focus_search_entry()

    def get_home_box(self):
        return self._home_box
