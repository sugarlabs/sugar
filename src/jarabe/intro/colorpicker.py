# Copyright (C) 2007, Red Hat, Inc.
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

from sugar4.graphics.icon import Icon
from sugar4.graphics import style
from sugar4.graphics.xocolor import XoColor


class ColorPicker(Gtk.Box):

    def __init__(self):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        self.set_can_target(True)
        self.set_focusable(True)
        self.set_can_focus(True)
        self._xo_color = None

        self._xo = Icon(pixel_size=style.XLARGE_ICON_SIZE,
                        icon_name='computer-xo')
        self._set_random_colors()

        gesture = Gtk.GestureClick()
        gesture.connect('pressed', self._button_press_cb)
        self.add_controller(gesture)

        self.append(self._xo)
        self._xo.show()

    def _button_press_cb(self, gesture, n_press, x, y):
        self._set_random_colors()

    def get_color(self):
        return self._xo_color

    def _set_random_colors(self):
        self._xo_color = XoColor()
        self._xo.props.xo_color = self._xo_color
