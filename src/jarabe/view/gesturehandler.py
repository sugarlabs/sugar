# Copyright (C) 2012 One Laptop Per Child
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

import gi
gi.require_version('SugarExt', '2.0')

from gi.repository import Gdk
from gi.repository import SugarExt

try:
    from gi.repository import Gtk
except ImportError:
    Gtk = None

from sugar4.graphics import style

import logging

_instance = None


class GestureHandler(object):
    '''Handling gestures to show/hide the frame using GTK4 standard event controllers'''

    def __init__(self, frame):
        self._frame = frame
        self._controller = Gtk.GestureSwipe.new()
        self._controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self._controller.connect('swipe', self.__swipe_cb)
        
        # Attach to master window
        from jarabe.model import shell
        app = shell.get_model()
        if app:
            windows = app.get_windows()
            if windows:
                windows[0].add_controller(self._controller)

    def __swipe_cb(self, gesture, velocity_x, velocity_y):
        # A simple swipe detection: if velocity is high enough, toggle frame
        if abs(velocity_x) > 500 or abs(velocity_y) > 500:
            self._frame.toggle()


def setup(frame):
    global _instance
    _instance = GestureHandler(frame)
