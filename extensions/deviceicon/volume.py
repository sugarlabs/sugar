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

import logging

import gobject
import gio
import gtk
import gconf

from sugar.graphics.tray import TrayIcon
from sugar.graphics.xocolor import XoColor

from jarabe.journal import journalactivity
from jarabe.view.palettes import VolumePalette
from jarabe.frame.frameinvoker import FrameWidgetInvoker


_icons = {}


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 500

    def __init__(self, mount):

        self._mount = mount

        icon_name = None
        icon_theme = gtk.icon_theme_get_default()
        for icon_name in self._mount.get_icon().props.names:
            icon_info = icon_theme.lookup_icon(icon_name,
                                               gtk.ICON_SIZE_LARGE_TOOLBAR, 0)
            if icon_info is not None:
                break

        if icon_name is None:
            icon_name = 'drive'

        # TODO: retrieve the colors from the owner of the device
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=icon_name, xo_color=color)

        self.set_palette_invoker(FrameWidgetInvoker(self))

        self.connect('button-release-event', self.__button_release_event_cb)

    def create_palette(self):
        palette = VolumePalette(self._mount)
        palette.set_group_id('frame')
        return palette

    def __button_release_event_cb(self, widget, event):
        journal = journalactivity.get_journal()
        journal.set_active_volume(self._mount)
        journal.reveal()
        return True


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
    # Follow Nautilus behaviour here
    # since it has the same issue with removable device
    # and it would be good to not invent our own workflow
    if hasattr(volume, 'should_automount') and not volume.should_automount():
        return

    #TODO: should be done by some other process, like gvfs-hal-volume-monitor
    #TODO: use volume.should_automount() when it gets into pygtk
    if volume.get_mount() is None and volume.can_mount():
        #TODO: pass None as mount_operation, or better, SugarMountOperation
        volume.mount(gtk.MountOperation(tray.get_toplevel()), _mount_cb)


def _mount_cb(volume, result):
    logging.debug('_mount_cb %r %r', volume, result)
    volume.mount_finish(result)


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
