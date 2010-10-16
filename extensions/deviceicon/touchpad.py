# Copyright (C) 2010, Walter Bender, Sugar Labs
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
import os

import gtk
import gconf

import logging

from sugar.graphics.tray import TrayIcon
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import Palette
from sugar.graphics import style

from jarabe.frame.frameinvoker import FrameWidgetInvoker

TOUCHPAD_MODE_CAPACITIVE = 'capacitive'
TOUCHPAD_MODE_RESISTIVE = 'resistive'
TOUCHPAD_MODES = [TOUCHPAD_MODE_CAPACITIVE, TOUCHPAD_MODE_RESISTIVE]
STATUS_TEXT = {
    TOUCHPAD_MODE_CAPACITIVE: _('finger'),
    TOUCHPAD_MODE_RESISTIVE: _('stylus'),
}
STATUS_ICON = {
    TOUCHPAD_MODE_CAPACITIVE: 'touchpad-' + TOUCHPAD_MODE_CAPACITIVE,
    TOUCHPAD_MODE_RESISTIVE: 'touchpad-' + TOUCHPAD_MODE_RESISTIVE,
}
# NODE_PATH is used to communicate with the touchpad device.
NODE_PATH = '/sys/devices/platform/i8042/serio1/ptmode'


class DeviceView(TrayIcon):
    """ Manage the touchpad mode from the device palette on the Frame. """

    FRAME_POSITION_RELATIVE = 500

    def __init__(self):
        """ Create the icon that represents the touchpad. """
        icon_name = STATUS_ICON[_read_touchpad_mode()]

        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        TrayIcon.__init__(self, icon_name=icon_name, xo_color=color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.connect('button-release-event', self.__button_release_event_cb)

    def create_palette(self):
        """ Create a palette for this icon; called by the Sugar framework
        when a palette needs to be displayed. """
        self.palette = ResourcePalette(_('My touchpad'), self.icon)
        self.palette.set_group_id('frame')
        return self.palette

    def __button_release_event_cb(self, widget, event):
        """ Callback for button release event; used to invoke touchpad-mode
        change. """
        self.palette.toggle_mode()
        return True


class ResourcePalette(Palette):
    """ Palette attached to the decive icon that represents the touchpas. """

    def __init__(self, primary_text, icon):
        """ Create the palette and initilize with current touchpad status. """
        Palette.__init__(self, label=primary_text)

        self._icon = icon

        vbox = gtk.VBox()
        self.set_content(vbox)

        self._status_text = gtk.Label()
        vbox.pack_start(self._status_text, padding=style.DEFAULT_PADDING)
        self._status_text.show()

        vbox.show()

        self._mode = _read_touchpad_mode()
        self._update()

    def _update(self):
        """ Update the label and icon based on the current mode. """
        self._status_text.set_label(STATUS_TEXT[self._mode])
        self._icon.props.icon_name = STATUS_ICON[self._mode]

    def toggle_mode(self):
        """ Toggle the touchpad mode. """
        self._mode = TOUCHPAD_MODES[1 - TOUCHPAD_MODES.index(self._mode)]
        _write_touchpad_mode(self._mode)
        self._update()


def setup(tray):
    """ Initialize the devic icon; called by the shell when initializing the
    Frame. """
    if os.path.exists(NODE_PATH):
        tray.add_device(DeviceView())
        _write_touchpad_mode(TOUCHPAD_MODE_CAPACITIVE)


def _read_touchpad_mode():
    """ Read the touchpad mode from the node path. """
    node_file_handle = open(NODE_PATH, 'r')
    text = node_file_handle.read()
    node_file_handle.close()

    return TOUCHPAD_MODES[int(text[0])]


def _write_touchpad_mode(touchpad):
    """ Write the touchpad mode to the node path. """
    try:
        node_file_handle = open(NODE_PATH, 'w')
    except IOError, e:
        logging.error('Error opening %s for writing: %s', NODE_PATH, e)
        return
    node_file_handle.write(str(TOUCHPAD_MODES.index(touchpad)))
    node_file_handle.close()
