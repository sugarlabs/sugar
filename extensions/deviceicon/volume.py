# Copyright (C) 2008 One Laptop Per Child
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

from sugar.graphics.tray import TrayIcon

from jarabe.model import volume

_icons = {}

class DeviceView(TrayIcon):
    FRAME_POSITION_RELATIVE = 800
    def __init__(self, volume):
        TrayIcon.__init__(self, icon_name=volume.icon_name,
                          xo_color=volume.icon_color)

def setup(tray):
    volumes_manager = volume.get_volumes_manager()

    for vol in volumes_manager.get_volumes():
        _add_device(vol, tray)

    volumes_manager.connect('volume-added', _volume_added_cb, tray)
    volumes_manager.connect('volume-removed', _volume_removed_cb, tray)

def _volume_added_cb(volumes_manager, vol, tray):
    _add_device(vol, tray)

def _volume_removed_cb(volumes_manager, vol, tray):
    _remove_device(vol, tray)

def _add_device(volume, tray):
    icon = DeviceView(volume)
    _icons[volume] = icon
    tray.add_device(icon)

def _remove_device(volume, tray):
    icon = _icons[volume]
    tray.remove_device(icon)
    del _icons[volume]

