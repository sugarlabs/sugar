# Copyright (C) 2012 One Laptop Per Child
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

import logging

from gi.repository import Gdk

from gi.repository import SugarExt

_instance = None


def setup():
    '''Cursor tracker: only display the cursor in mouse/trackpad mode

    We only display the cursor in mouse/trackpad mode, hence when
    a mouse motion is detected or a button press event. When a
    touch begin event is received the cursor will be hidden.

    We only track the incoming events when a touchscreen device
    is available.

    '''
    global _instance

    display = Gdk.Display.get_default()
    device_manager = display.get_device_manager()
    devices = device_manager.list_devices(Gdk.DeviceType.SLAVE)
    for device in devices:
        if device.get_source() == Gdk.InputSource.TOUCHSCREEN:
            logging.debug('Cursor Tracker: found touchscreen, '
                          'will track input.')
            _instance = SugarExt.CursorTracker()
            break

    if not _instance:
        logging.debug('Cursor Tracker: no touchscreen available, '
                      'will not track input.')
