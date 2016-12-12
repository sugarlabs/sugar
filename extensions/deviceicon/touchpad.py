# Copyright (C) 2010, Walter Bender, Sugar Labs
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


from gettext import gettext as _
import os

from gi.repository import Gtk

import logging

from sugar3 import profile
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palette import Palette
from sugar3.graphics import style

from jarabe.frame.frameinvoker import FrameWidgetInvoker

TOUCHPAD_MODE_MOUSE = 'mouse'
TOUCHPAD_MODE_PENTABLET = 'pentablet'

TOUCHPAD_MODES = (TOUCHPAD_MODE_MOUSE, TOUCHPAD_MODE_PENTABLET)
STATUS_TEXT = (_('finger'), _('stylus'))
STATUS_ICON = ('touchpad-capacitive', 'touchpad-resistive')

# NODE_PATH is used to communicate with the touchpad device.
NODE_PATH = '/sys/devices/platform/i8042/serio1/hgpk_mode'


class DeviceView(TrayIcon):
    """ Manage the touchpad mode from the device palette on the Frame. """

    FRAME_POSITION_RELATIVE = 500

    def __init__(self):
        """ Create the icon that represents the touchpad. """
        icon_name = STATUS_ICON[_read_touchpad_mode()]

        color = profile.get_color()
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

        vbox = Gtk.VBox()
        self.set_content(vbox)

        self._status_text = Gtk.Label()
        vbox.pack_start(self._status_text, True, True, style.DEFAULT_PADDING)
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
        self._mode = 1 - self._mode
        _write_touchpad_mode(self._mode)
        self._update()


def setup(tray):
    """ Initialize the devic icon; called by the shell when initializing the
    Frame. """
    if os.path.exists(NODE_PATH):
        tray.add_device(DeviceView())
        _write_touchpad_mode_str(TOUCHPAD_MODE_MOUSE)


def _read_touchpad_mode_str():
    """ Read the touchpad mode string from the node path. """
    node_file_handle = open(NODE_PATH, 'r')
    text = node_file_handle.read().strip().lower()
    node_file_handle.close()
    return text


def _read_touchpad_mode():
    """ Read the touchpad mode and return the mode index. """
    mode_str = _read_touchpad_mode_str()
    if mode_str not in TOUCHPAD_MODES:
        return None
    return TOUCHPAD_MODES.index(mode_str)


def _write_touchpad_mode_str(mode_str):
    """ Write the touchpad mode to the node path. """
    try:
        node_file_handle = open(NODE_PATH, 'w')
    except IOError, e:
        logging.error('Error opening %s for writing: %s', NODE_PATH, e)
        return
    node_file_handle.write(mode_str)
    node_file_handle.close()


def _write_touchpad_mode(mode_num):
    """ Look up the mode (by index) and write to node path. """
    return _write_touchpad_mode_str(TOUCHPAD_MODES[mode_num])
