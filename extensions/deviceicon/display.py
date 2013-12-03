# -*- coding: utf-8 -*-
# Copyright (C) 2013 SugarLabs
# Copyright (C) 2013 Ignacio Rodríguez <ignacio@sugarlabs.org>
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

from gettext import gettext as _

from gi.repository import GConf
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import GObject

from sugar3.graphics.icon import Icon
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.xocolor import XoColor

from jarabe import frame
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.view.screenshot import take_screenshot

_ICON_NAME = 'camera-external'


class DisplayDeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 500

    def __init__(self):
        client = GConf.Client.get_default()
        self._color = XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)

        self.set_palette_invoker(FrameWidgetInvoker(self))

    def create_palette(self):
        label = GLib.markup_escape_text(_('My display'))
        palette = DisplayPalette(label)
        palette.set_group_id('frame')
        return palette


class DisplayPalette(Palette):

    def __init__(self, primary_text):
        Palette.__init__(self, primary_text)

        box = PaletteMenuBox()
        self.set_content(box)
        box.show()

        self._screenshot_item = PaletteMenuItem(_('Take a screenshot'))
        icon = Icon(icon_name=_ICON_NAME, icon_size=Gtk.IconSize.MENU)
        self._screenshot_item.set_image(icon)

        box.append_item(self._screenshot_item)
        self._screenshot_item.show()
        icon.show()

        self._screenshot_item.connect('activate',
                                      self.__screenshot_activate_cb)

    def __screenshot_activate_cb(self, menuitem_):
        frame_ = frame.get_view()
        frame_.hide()
        GObject.idle_add(self._take_screenshot, frame_)

    def _take_screenshot(self, frame_):
        if frame_.is_visible():
            return True

        take_screenshot()
        frame_.show()
        return False


def setup(tray):
    tray.add_device(DisplayDeviceView())
