# Copyright (C) 2006, Red Hat, Inc.
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
from gi.repository import GConf
import logging

from sugar3.graphics.icon import Icon
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor


class KeepIcon(Gtk.ToggleButton):
    def __init__(self):
        GObject.GObject.__init__(self)
        self.set_relief(Gtk.ReliefStyle.NONE)
        self.set_focus_on_click(False)

        self._icon = Icon(icon_name='emblem-favorite',
                          pixel_size=style.SMALL_ICON_SIZE)
        self.set_image(self._icon)
        self.connect('toggled', self.__toggled_cb)
        self.connect('leave-notify-event', self.__leave_notify_event_cb)
        self.connect('enter-notify-event', self.__enter_notify_event_cb)

    def __toggled_cb(self, widget):
        if self.get_active():
            client = GConf.Client.get_default()
            color = XoColor(client.get_string('/desktop/sugar/user/color'))
            self._icon.props.xo_color = color
            logging.debug('KEEPICON: setting xo_color')
        else:
            self._icon.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self._icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def __enter_notify_event_cb(self, icon, event):
        if not self.get_active():
            self._icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()

    def __leave_notify_event_cb(self, icon, event):
        if not self.get_active():
            self._icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
