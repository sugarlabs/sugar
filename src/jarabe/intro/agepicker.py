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

from gettext import gettext as _

from sugar3.graphics.icon import EventIcon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor

AGES = [3, 5, 7, 9, 11, 12, 15, 25]
AGE_LABELS = [_('0-3'), _('4-5'), _('6-7'), _('8-9'), _('10-11'), _('12'),
              _('13-17'), _('Adult')]


class AgePicker(Gtk.Grid):

    def __init__(self, gender):
        Gtk.Grid.__init__(self)
        self.set_row_spacing(style.DEFAULT_SPACING)
        self.set_column_spacing(style.DEFAULT_SPACING)

        self._gender = gender
        self._age = 5
        self._buttons = []
        self._nocolor = XoColor('#010101,#ffffff')
        self._color = XoColor()

        if self._gender is None or self._gender == 'None':
            self._gender = 'male'

        for i in range(len(AGES)):
            self._buttons.append(
                EventIcon(pixel_size=style.LARGE_ICON_SIZE,
                          icon_name='%s-%d' % (self._gender, i)))
            self._buttons[-1].show()
            self._buttons[-1].connect('button-press-event',
                                      self._button_press_cb, i)

            label = Gtk.Label()
            label.set_text(AGE_LABELS[i])
            label.show()

            self.attach(self._buttons[-1], i, 0, 1, 1)
            self.attach(label, i, 1, 1, 1)

    def _button_press_cb(self, widget, event, age):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            if self._age is not None:
                self._buttons[self._age].xo_color = self._nocolor
            self._set_age(age)
            self._buttons[age].xo_color = self._color

    def get_age(self):
        if self._age is None:
            return None
        else:
            return AGES[self._age]

    def _set_age(self, age):
        self._age = age

    def update_color(self, color):
        self._color = color
        if self._age is not None:
            self._buttons[self._age].xo_color = self._color

    def update_gender(self, gender):
        self._gender = gender
        for i in range(8):
            self._buttons[i].set_icon_name('%s-%d' % (self._gender, i))
            self._buttons[i].show()
