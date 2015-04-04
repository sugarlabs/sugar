# Copyright (C) 2012, OLPC
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

import logging
from gettext import gettext as _

from gi.repository import GConf

from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics.xocolor import XoColor

from jarabe.frame.frameinvoker import FrameWidgetInvoker
import jarabe.frame

_ICON_NAME = 'module-keyboard'
_HAS_MALIIT = False

try:
    from gi.repository import Maliit
except ImportError:
    logging.debug('Frame: can not create OSK icon: Maliit is not installed.')
    _HAS_MALIIT = False
else:
    _HAS_MALIIT = True


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 103

    def __init__(self):
        client = GConf.Client.get_default()
        self._color = XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=_ICON_NAME, xo_color=self._color)

        self._input_method = Maliit.InputMethod()
        self.connect('button-release-event', self.__button_release_event_cb)
        self.set_palette_invoker(FrameWidgetInvoker(self))

    def create_palette(self):
        palette = Palette(_('Show my keyboard'))
        palette.set_group_id('frame')
        return palette

    def __button_release_event_cb(self, widget, event):
        self._input_method.show()
        frame = jarabe.frame.get_view()
        frame.hide()


def setup(tray):
    return
    # Disable the option for now, as manual invocation
    # of the OSK has many unresolved corner cases, see
    # http://dev.laptop.org/ticket/12281

    if _HAS_MALIIT:
        tray.add_device(DeviceView())
