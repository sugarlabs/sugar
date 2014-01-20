# Copyright (C) 2014, Sugar Labs
# Copyright (C) 2014, Walter Bender
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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA

from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import EventIcon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor


GENDERS = ['female', 'male']


class GenderPicker(Gtk.Grid):
    def __init__(self):
        Gtk.Grid.__init__(self)
        self.set_row_spacing(style.DEFAULT_SPACING)
        self.set_column_spacing(style.DEFAULT_SPACING)

        self._gender = None
        self._buttons = []
        self._nocolor = XoColor('#010101,#ffffff')
        self._color = XoColor()

        for i, gender in enumerate(GENDERS):
            self._buttons.append(EventIcon(pixel_size=style.XLARGE_ICON_SIZE,
                                           icon_name='%s-6' % (gender)))
            self._buttons[-1].show()
            self._buttons[-1].connect('button-press-event',
                                      self._button_press_cb, i)

            self.attach(self._buttons[-1], i, 0, 1, 1)

    def _button_press_cb(self, widget, event, gender_index):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            self._set_gender(GENDERS[gender_index])
            self._buttons[gender_index].xo_color = self._color
            self._buttons[1 - gender_index].xo_color = self._nocolor

    def get_gender(self):
        return self._gender

    def _set_gender(self, gender):
        self._gender = gender

    def update_color(self, color):
        self._color = color
        if self._gender in GENDERS:
            self._buttons[GENDERS.index(self._gender)].xo_color = self._color
