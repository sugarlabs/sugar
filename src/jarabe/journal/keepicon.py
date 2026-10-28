# Copyright (C) 2006, Red Hat, Inc.
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

from sugar4.graphics.icon import Icon
from sugar4.graphics import style
from sugar4 import profile


class KeepIcon(Gtk.ToggleButton):
    __gtype_name__ = 'SugarKeepIcon'

    def __init__(self):
        super().__init__()
        self.props.has_frame = False
        self.props.focusable = False

        self._icon = Icon(icon_name='emblem-favorite',
                          pixel_size=style.SMALL_ICON_SIZE)
        self.set_child(self._icon)
        self.connect('toggled', self.__toggled_cb)

        click = Gtk.GestureClick()
        click.connect('pressed', self.__button_press_event_cb)
        click.connect('released', self.__button_release_event_cb)
        self.add_controller(click)

        self._xo_color = profile.get_color()

        self.set_size_request(style.GRID_CELL_SIZE, style.GRID_CELL_SIZE)

    def __button_press_event_cb(self, gesture, n_press, x, y):
        # We need to use a custom CSS class because in togglebuttons
        # the 'active' class doesn't only match the button press, they
        # can be left in the active state.
        self.add_css_class('toggle-press')

    def __button_release_event_cb(self, gesture, n_press, x, y):
        self.remove_css_class('toggle-press')

    def __toggled_cb(self, widget):
        if self.get_active():
            self._icon.props.xo_color = self._xo_color
        else:
            self._icon.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self._icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

if hasattr(KeepIcon, 'set_css_name'):
    KeepIcon.set_css_name('canvasicon')
