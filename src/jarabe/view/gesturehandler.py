# Copyright (C) 2012 One Laptop Per Child
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

from gi.repository import Gdk

from gi.repository import SugarExt
from gi.repository import SugarGestures

from sugar3.graphics import style

_instance = None


class GestureHandler(object):
    '''Handling gestures to show/hide the frame

    We use SugarExt.GestureGrabber to listen for
    gestures on the root window. Swiping from
    the frame area towards the center does reveal
    the Frame. Swiping towards one of the edges
    does hide the Frame.
    '''

    _HIDE = 0
    _SHOW = 1

    def __init__(self, frame):
        self._frame = frame

        self._gesture_grabber = SugarExt.GestureGrabber()

        rectangle = self._create_rectangle(0, 0, Gdk.Screen.width(),
                                           style.GRID_CELL_SIZE)
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.DOWN)
        swipe.connect('swipe-ended', self.__top_show_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle(0, 0, Gdk.Screen.width(),
                                           style.GRID_CELL_SIZE * 2)
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.UP)
        swipe.connect('swipe-ended', self.__top_hide_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle( \
            0, Gdk.Screen.height() - style.GRID_CELL_SIZE,
            Gdk.Screen.width(), style.GRID_CELL_SIZE)
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.UP)
        swipe.connect('swipe-ended', self.__bottom_show_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle( \
            0, Gdk.Screen.height() - style.GRID_CELL_SIZE * 2,
            Gdk.Screen.width(), style.GRID_CELL_SIZE * 2)
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.DOWN)
        swipe.connect('swipe-ended', self.__bottom_hide_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle( \
                0, 0, style.GRID_CELL_SIZE, Gdk.Screen.height())
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.RIGHT)
        swipe.connect('swipe-ended', self.__left_show_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle( \
                0, 0, style.GRID_CELL_SIZE * 2, Gdk.Screen.height())
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.LEFT)
        swipe.connect('swipe-ended', self.__left_hide_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle( \
                Gdk.Screen.width() - style.GRID_CELL_SIZE, 0,
                style.GRID_CELL_SIZE, Gdk.Screen.height())
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.LEFT)
        swipe.connect('swipe-ended', self.__right_show_cb)
        self._gesture_grabber.add(swipe, rectangle)

        rectangle = self._create_rectangle( \
                Gdk.Screen.width() - style.GRID_CELL_SIZE * 2, 0,
                style.GRID_CELL_SIZE * 2, Gdk.Screen.height())
        swipe = SugarGestures.SwipeController( \
            directions=SugarGestures.SwipeDirectionFlags.RIGHT)
        swipe.connect('swipe-ended', self.__right_hide_cb)
        self._gesture_grabber.add(swipe, rectangle)

    def _create_rectangle(self, x, y, width, height):
        rect = Gdk.Rectangle()
        rect.x = x
        rect.y = y
        rect.width = width
        rect.height = height
        return rect

    def __top_show_cb(self, controller, event_direction):
        self._frame.show()

    def __top_hide_cb(self, controller, event_direction):
        self._frame.hide()

    def __bottom_show_cb(self, controller, event_direction):
        self._frame.show()

    def __bottom_hide_cb(self, controller, event_direction):
        self._frame.hide()

    def __left_show_cb(self, controller, event_direction):
        self._frame.show()

    def __left_hide_cb(self, controller, event_direction):
        self._frame.hide()

    def __right_show_cb(self, controller, event_direction):
        self._frame.show()

    def __right_hide_cb(self, controller, event_direction):
        self._frame.hide()


def setup(frame):
    global _instance

    if _instance:
        del _instance

    _instance = GestureHandler(frame)
