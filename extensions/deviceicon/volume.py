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

import os
import statvfs
from gettext import gettext as _

import gtk

from sugar.graphics.tray import TrayIcon
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon

from jarabe.model import volume
from jarabe.journal import journalactivity

_icons = {}

class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 800

    def __init__(self, model):
        TrayIcon.__init__(self, icon_name=model.icon_name,
                          xo_color=model.icon_color)
        self._model = model
        self.connect('button-release-event', self.__button_release_event_cb)

    def create_palette(self):
        return VolumePalette(self._model)

    def __button_release_event_cb(self, widget, event):
        journal = journalactivity.get_journal()
        journal.set_active_volume(self._model.mount_point)
        journal.present()
        return True

class VolumePalette(Palette):
    def __init__(self, model):
        Palette.__init__(self, label=model.name,
                         secondary_text=model.mount_point)
        self._model = model

        vbox = gtk.VBox()
        self.set_content(vbox)
        vbox.show()

        self._progress_bar = gtk.ProgressBar()
        vbox.add(self._progress_bar)
        self._progress_bar.show()

        self._free_space_label = gtk.Label()
        self._free_space_label.set_alignment(0.5, 0.5)
        vbox.add(self._free_space_label)
        self._free_space_label.show()

        self.connect('popup', self.__popup_cb)

        menu_item = MenuItem(_('Unmount'))

        icon = Icon(icon_name='media-eject', icon_size=gtk.ICON_SIZE_MENU)
        menu_item.set_image(icon)
        icon.show()

        menu_item.connect('activate', self.__unmount_activate_cb)
        self.menu.append(menu_item)
        menu_item.show()

    def __unmount_activate_cb(self, menu_item):
        self._model.unmount()

    def __popup_cb(self, palette):
        stat = os.statvfs(self._model.mount_point)
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MB Free') % \
                {'free_space': free_space / (1024 * 1024)}

def setup(tray):
    volumes_manager = volume.get_volumes_manager()

    for vol in volumes_manager.get_volumes():
        if vol.mount_point != '/':
            _add_device(vol, tray)

    volumes_manager.connect('volume-added', _volume_added_cb, tray)
    volumes_manager.connect('volume-removed', _volume_removed_cb, tray)

def _volume_added_cb(volumes_manager, vol, tray):
    if vol.mount_point != '/':
        _add_device(vol, tray)

def _volume_removed_cb(volumes_manager, vol, tray):
    _remove_device(vol, tray)

def _add_device(vol, tray):
    icon = DeviceView(vol)
    _icons[vol] = icon
    tray.add_device(icon)

def _remove_device(vol, tray):
    icon = _icons[vol]
    tray.remove_device(icon)
    del _icons[vol]
