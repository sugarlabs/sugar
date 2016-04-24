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

from gi.repository import Gdk

from gi.repository import SugarExt
from gi.repository import SugarGestures

from sugar3.graphics import style

_instance = None


class GestureHandler(object):
    '''Handling gestures to show/hide the frame

    We use SugarExt.GestureGrabber to listen for
    gestures on the root window. We use a toggle
    gesture to either hide or show the frame: Swiping
    from the frame area at the top towards the center
    does reveal the Frame or hide it.
    '''

    def __init__(self, frame):
        self._frame = frame

        self._gesture_grabber = SugarExt.GestureGrabber()
        self._controller = []

        screen = Gdk.Screen.get_default()
        screen.connect('size-changed', self.__size_changed_cb)

        self._add_controller()

    def __size_changed_cb(self, screen):
        self._add_controller()

    def _add_controller(self):
        for controller in self._controller:
            self._gesture_grabber.remove(controller)

        self._track_gesture_for_area(SugarGestures.SwipeDirectionFlags.DOWN,
                                     0, 0, Gdk.Screen.width(),
                                     style.GRID_CELL_SIZE)

    def _track_gesture_for_area(self, directions, x, y, width, height):
        rectangle = Gdk.Rectangle()
        rectangle.x = x
        rectangle.y = y
        rectangle.width = width
        rectangle.height = height
        swipe = SugarGestures.SwipeController(directions=directions)
        swipe.connect('swipe-ended', self.__swipe_ended_cb)
        self._gesture_grabber.add(swipe, rectangle)
        self._controller.append(swipe)

    def __swipe_ended_cb(self, controller, event_direction):
        self._frame.toggle()


def setup(frame):
    global _instance
    _instance = GestureHandler(frame)
