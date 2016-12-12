# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2014, Ignacio Rodriguez
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
from gettext import gettext as _

from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gtk

from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.icon import Icon
from sugar3.graphics import style

from jarabe.journal import journalactivity
from jarabe.journal.misc import get_mount_icon_name
from jarabe.journal.misc import get_mount_color
from jarabe.view.palettes import VolumePalette
from jarabe.frame.frameinvoker import FrameWidgetInvoker


_icons = {}
volume_monitor = None


class DeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 500

    def __init__(self, mount):

        self._mount = mount
        self._icon_name = get_mount_icon_name(mount,
                                              Gtk.IconSize.LARGE_TOOLBAR)
        # TODO: retrieve the colors from the owner of the device
        color = get_mount_color(self._mount)

        TrayIcon.__init__(self, icon_name=self._icon_name, xo_color=color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True

    def create_palette(self):
        palette = VolumePalette(self._mount)
        palette.set_group_id('frame')

        menu_item = PaletteMenuItem(_('Show contents'))
        color = get_mount_color(self._mount)
        icon = Icon(icon_name=self._icon_name,
                    pixel_size=style.SMALL_ICON_SIZE,
                    xo_color=color)
        menu_item.set_image(icon)
        icon.show()

        menu_item.connect('activate', self.__show_contents_cb)
        palette.content_box.pack_start(menu_item, True, True, 0)
        palette.content_box.reorder_child(menu_item, 0)
        menu_item.show()

        return palette

    def __show_contents_cb(self, menu_item):
        journal = journalactivity.get_journal()
        journal.set_active_volume(self._mount)
        journal.reveal()


def setup(tray):
    GLib.idle_add(_setup_volumes, tray)


def _setup_volumes(tray):
    global volume_monitor
    volume_monitor = Gio.VolumeMonitor.get()

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
    if not volume.should_automount():
        return

    # TODO: should be done by some other process, like gvfs-hal-volume-monitor
    if volume.get_mount() is None and volume.can_mount():
        # TODO: pass None as mount_operation, or better, SugarMountOperation
        flags = 0
        mount_operation = Gtk.MountOperation(parent=tray.get_toplevel())
        cancellable = None
        user_data = None
        volume.mount(flags, mount_operation, cancellable, _mount_cb, user_data)


def _mount_cb(volume, result, user_data):
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
