# Copyright (C) 2014, Sugar Labs
# Copyright (C) 2014, Walter Bender
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
from gi.repository import Gio
from gi.repository import GObject

from sugar3.graphics.icon import EventIcon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor


GENDERS = ['female', 'male']


def load_gender():
    settings = Gio.Settings('org.sugarlabs.user')
    return settings.get_string('gender')


def save_gender(gender):
    settings = Gio.Settings('org.sugarlabs.user')
    if gender is not None:
        settings.set_string('gender', gender)
    else:
        settings.set_string('gender', '')

    # DEPRECATED
    from gi.repository import GConf
    if gender is not None:
        client = GConf.Client.get_default()
        client.set_string('/desktop/sugar/user/gender', gender)


class GenderPicker(Gtk.Grid):

    gender_changed_signal = GObject.Signal('gender-changed', arg_types=([str]))

    def __init__(self):
        Gtk.Grid.__init__(self)
        self.set_row_spacing(style.DEFAULT_SPACING)
        self.set_column_spacing(style.DEFAULT_SPACING)

        self._gender = load_gender()
        self._buttons = []
        self._nocolor = XoColor('#010101,#ffffff')
        self._color = XoColor()

        for i, gender in enumerate(GENDERS):
            self._buttons.append(EventIcon(pixel_size=style.XLARGE_ICON_SIZE,
                                           icon_name='%s-6' % (gender)))
            self._buttons[-1].connect('activate',
                                      self._button_activate_cb, i)
            self.attach(self._buttons[-1], i * 2, 0, 1, 1)
            self._buttons[-1].show()

        self.reset_button = EventIcon(pixel_size=style.SMALL_ICON_SIZE,
                                      icon_name='entry-cancel')
        self.reset_button.connect('activate',
                                  self._reset_button_activate_cb)
        self.attach(self.reset_button, 1, 0, 1, 1)
        self.reset_button.xo_color = XoColor('#010101,#a0a0a0')
        self.reset_button.show()

    def _reset_button_activate_cb(self, widget):
        self._set_gender('')
        for i in range(len(GENDERS)):
            self._buttons[i].xo_color = self._nocolor

    def _button_activate_cb(self, widget, gender_index):
        self._set_gender(GENDERS[gender_index])
        self._buttons[gender_index].xo_color = self._color
        self._buttons[1 - gender_index].xo_color = self._nocolor

    def get_gender(self):
        return self._gender

    def _set_gender(self, gender):
        self.gender_changed_signal.emit(gender)
        self._gender = gender

    def update_color(self, color):
        self._color = color
        if self._gender in GENDERS:
            self._buttons[GENDERS.index(self._gender)].xo_color = self._color
