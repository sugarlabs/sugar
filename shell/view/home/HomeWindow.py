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
import hippo
import cairo

from sugar.graphics import style

from view.home.MeshBox import MeshBox
from view.home.HomeBox import HomeBox
from view.home.FriendsBox import FriendsBox
from view.home.transitionbox import TransitionBox
from model.shellmodel import ShellModel

_HOME_PAGE       = 0
_FRIENDS_PAGE    = 1
_MESH_PAGE       = 2
_TRANSITION_PAGE = 3

class HomeWindow(gtk.Window):
    def __init__(self, shell):
        gtk.Window.__init__(self)

        self._shell = shell
        self._active = False
        self._level = ShellModel.ZOOM_HOME

        self._canvas = hippo.Canvas()
        self.add(self._canvas)
        self._canvas.show()

        self.set_default_size(gtk.gdk.screen_width(),
                              gtk.gdk.screen_height())

        self.realize()
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DESKTOP)
        self.connect("key-release-event", self._key_release_cb)
        self.connect('focus-in-event', self._focus_in_cb)
        self.connect('focus-out-event', self._focus_out_cb)

        self._enter_sid = self.connect('enter-notify-event',
                                       self._enter_notify_event_cb)
        self._leave_sid = self.connect('leave-notify-event',
                                       self._leave_notify_event_cb)
        self._motion_sid = self.connect('motion-notify-event',
                                        self._motion_notify_event_cb)

        self._home_box = HomeBox(shell)
        self._friends_box = FriendsBox(shell)
        self._mesh_box = MeshBox(shell)
        self._transition_box = TransitionBox()

        self._activate_view()
        self._canvas.set_root(self._home_box)
        
        self._transition_box.connect('completed',
                                     self._transition_completed_cb)

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

    def _key_release_cb(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname == "Alt_L":
            self._home_box.release()

    def _deactivate_view(self):
        if self._level == ShellModel.ZOOM_HOME:
            self._home_box.suspend()
        elif self._level == ShellModel.ZOOM_MESH:
            self._mesh_box.suspend()

    def _activate_view(self):
        if self._level == ShellModel.ZOOM_HOME:
            self._home_box.resume()
        elif self._level == ShellModel.ZOOM_MESH:
            self._mesh_box.resume()

    def _focus_in_cb(self, widget, event):
        self._activate_view()

    def _focus_out_cb(self, widget, event):
        self._deactivate_view()

    def set_zoom_level(self, level):
        self._deactivate_view()
        self._level = level
        self._activate_view()
    
        self._canvas.set_root(self._transition_box)

        if level == ShellModel.ZOOM_HOME:
            size = style.XLARGE_ICON_SIZE
        elif level == ShellModel.ZOOM_FRIENDS:
            size = style.LARGE_ICON_SIZE
        elif level == ShellModel.ZOOM_MESH:
            size = style.STANDARD_ICON_SIZE
            
        self._transition_box.set_size(size)
    
    def _transition_completed_cb(self, transition_box):
        if self._level == ShellModel.ZOOM_HOME:
            self._canvas.set_root(self._home_box)
        elif self._level == ShellModel.ZOOM_FRIENDS:
            self._canvas.set_root(self._friends_box)
        elif self._level == ShellModel.ZOOM_MESH:
            self._canvas.set_root(self._mesh_box)

    def get_home_box(self):
        return self._home_box   
