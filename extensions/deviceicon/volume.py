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
import logging

import gobject
import gio
import gtk
import gconf

from sugar.graphics.tray import TrayIcon
from sugar.graphics.palette import Palette
from sugar.graphics.menuitem import MenuItem
from sugar.graphics.icon import Icon
from sugar.graphics.xocolor import XoColor

from jarabe.journal import journalactivity

_icons = {}

class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 800

    def __init__(self, mount):
        TrayIcon.__init__(self)
        self._mount = mount

        # TODO: fallback to the more generic icons when needed
        self.get_icon().props.icon_name = self._mount.get_icon().props.names[0]

        # TODO: retrieve the colors from the owner of the device
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.get_icon().props.xo_color = color

        self.connect('button-release-event', self.__button_release_event_cb)

    def create_palette(self):
        return VolumePalette(self._mount)

    def __button_release_event_cb(self, widget, event):
        journal = journalactivity.get_journal()
        journal.set_active_volume(self._mount)
        journal.present()
        return True

class VolumePalette(Palette):
    def __init__(self, mount):
        Palette.__init__(self, label=mount.get_name())
        self._mount = mount

        self.props.secondary_text = mount.get_root().get_path()

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
        self._mount.unmount(self.__unmount_cb)

    def __unmount_cb(self, source, result):
        logging.debug('__unmount_cb %r %r' % (source, result))

    def __popup_cb(self, palette):
        mount_point = self._mount.get_root().get_path()
        stat = os.statvfs(mount_point)
        free_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BAVAIL]
        total_space = stat[statvfs.F_BSIZE] * stat[statvfs.F_BLOCKS]

        fraction = (total_space - free_space) / float(total_space)
        self._progress_bar.props.fraction = fraction
        self._free_space_label.props.label = _('%(free_space)d MB Free') % \
                {'free_space': free_space / (1024 * 1024)}

def setup(tray):
    gobject.idle_add(_setup_volumes, tray)

def _setup_volumes(tray):
    volume_monitor = gio.volume_monitor_get()

    for volume in volume_monitor.get_volumes():
        _mount(volume, tray)

    for mount in volume_monitor.get_mounts():
        _add_device(mount, tray)

    volume_monitor.connect('volume-added', _volume_added_cb, tray)
    volume_monitor.connect('mount-added', _mount_added_cb, tray)
    volume_monitor.connect('mount-removed', _mount_removed_cb, tray)

def _volume_added_cb(volume_monitor, volume, tray):
    _mount(volume, tray)

def _mount(volume, tray):
    #TODO: this should be done by some other process, like gvfs-hal-volume-monitor
    #TODO: use volume.should_automount() when it gets into pygtk
    if volume.get_mount() is None and volume.can_mount():
        #TODO: pass None as mount_operation, or better, SugarMountOperation
        volume.mount(gtk.MountOperation(tray.get_toplevel()), _mount_cb)

def _mount_cb(source, result):
    logging.debug('mount finished %r %r' % (source, result))

def _mount_added_cb(volume_monitor, mount, tray):
    _add_device(mount, tray)

def _mount_removed_cb(volume_monitor, mount, tray):
    icon = _icons[mount]
    tray.remove_device(icon)
    del _icons[mount]

def _add_device(mount, tray):
    icon = DeviceView(mount)
    _icons[mount] = icon
    tray.add_device(icon)

