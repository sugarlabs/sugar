# Copyright (C) 2007, Red Hat, Inc.
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

from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import EventIcon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor

import logging


class GenderPicker(Gtk.HBox):
    def __init__(self):
        Gtk.HBox.__init__(self)
        self._gender = None
        self._buttons = []
        self._nocolor = XoColor('#010101,#ffffff')
        self._color = XoColor()

        alignment = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        self.pack_start(alignment, expand=True, fill=True, padding=0)

        hbox = Gtk.HBox(spacing=style.DEFAULT_SPACING)
        alignment.add(hbox)

        eventbox = Gtk.EventBox()
        self._buttons.append(EventIcon(pixel_size=style.XLARGE_ICON_SIZE,
                                       icon_name='female-6'))
        self._buttons[-1].show()
        eventbox.connect('button-press-event', self._button_press_cb, 'female')
        eventbox.add(self._buttons[-1])
        eventbox.show()
        hbox.pack_start(eventbox, False, False, 0)

        eventbox = Gtk.EventBox()
        self._buttons.append(EventIcon(pixel_size=style.XLARGE_ICON_SIZE,
                                       icon_name='male-6'))
        self._buttons[-1].show()
        eventbox.connect('button-press-event', self._button_press_cb, 'male')
        eventbox.add(self._buttons[-1])
        eventbox.show()
        hbox.pack_start(eventbox, False, False, 0)

        self.show_all()

    def _button_press_cb(self, widget, event, gender):
        if event.button == 1 and event.type == Gdk.EventType.BUTTON_PRESS:
            logging.error('genderpicker: %s' % (gender))
            self._set_gender(gender)
            if gender == 'female':
                self._buttons[0].xo_color = self._color
                self._buttons[1].xo_color = self._nocolor
            else:
                self._buttons[1].xo_color = self._color
                self._buttons[0].xo_color = self._nocolor

    def get_gender(self):
        return self._gender

    def _set_gender(self, gender):
        self._gender = gender

    def update_color(self, color):
        self._color = color
        if self._gender == 'female':
            self._buttons[0].xo_color = self._color
        elif self._gender == 'male':
            self._buttons[1].xo_color = self._color
