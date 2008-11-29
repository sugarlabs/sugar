# Copyright (C) 2007, One Laptop Per Child
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

import gobject
import gio
import gtk
import gconf

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.palette import Palette
from sugar.graphics.xocolor import XoColor

from jarabe.journal import model

class VolumesToolbar(gtk.Toolbar):
    __gtype_name__ = 'VolumesToolbar'

    __gsignals__ = {
        'volume-changed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([object]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)
        self._volume_buttons = []
        self._mount_added_hid = None
        self._mount_removed_hid = None

        self.connect('destroy', self.__destroy_cb)

        gobject.idle_add(self._set_up_volumes)

    def __destroy_cb(self, widget):
        volume_monitor = gio.volume_monitor_get()
        volume_monitor.disconnect(self._mount_added_hid)
        volume_monitor.disconnect(self._mount_removed_hid)

    def _set_up_volumes(self):
        volume_monitor = gio.volume_monitor_get()
        self._mount_added_hid = \
                volume_monitor.connect('mount-added', self.__mount_added_cb)
        self._mount_removed_hid = \
                volume_monitor.connect('mount-removed', self.__mount_removed_cb)

        for mount in volume_monitor.get_mounts():
            self._add_button(mount)

    def __mount_added_cb(self, volume_monitor, mount):
        self._add_button(mount)

    def __mount_removed_cb(self, volume_monitor, mount):
        self._remove_button(mount)

    def _add_button(self, mount):
        logging.debug('VolumeToolbar._add_button: %r' % mount.get_name())

        if self._volume_buttons:
            group = self._volume_buttons[0]
        else:
            group = None

        palette = Palette(mount.get_name())

        button = VolumeButton(mount, group)
        button.set_palette(palette)
        button.connect('toggled', self._button_toggled_cb, mount)
        if self._volume_buttons:
            position = self.get_item_index(self._volume_buttons[-1]) + 1
        else:
            position = 0
        self.insert(button, position)
        button.show()

        self._volume_buttons.append(button)

        if mount.can_unmount():
            menu_item = gtk.MenuItem(_('Unmount'))
            menu_item.connect('activate', self._unmount_activated_cb, mount)
            palette.menu.append(menu_item)
            menu_item.show()

        if len(self.get_children()) > 1:
            self.show()

    def _button_toggled_cb(self, button, mount):
        if button.props.active:
            self.emit('volume-changed', mount)

    def _unmount_activated_cb(self, menu_item, mount):
        logging.debug('VolumesToolbar._unmount_activated_cb: %r', mount)
        mount.unmount(self.__unmount_cb)

    def __unmount_cb(self, source, result):
        logging.debug('__unmount_cb %r %r' % (source, result))

    def _get_button_for_mount(self, mount):
        for button in self.get_children():
            if button.mount == mount:
                return button
        logging.error('Couldnt find volume with mount %r' % mount)
        return None

    def _remove_button(self, mount):
        button = self._get_button_for_mount(mount)
        self._volume_buttons.remove(button)
        self.remove(button)
        self.get_children()[0].props.active = True

        if len(self.get_children()) < 2:
            self.hide()

    def set_active_volume(self, mount):
        button = self._get_button_for_mount(mount)
        button.props.active = True

class VolumeButton(RadioToolButton):
    def __init__(self, mount, group):
        RadioToolButton.__init__(self)

        # TODO: fallback to the more generic icons when needed
        self.props.named_icon = mount.get_icon().props.names[0]
        
        # TODO: retrieve the colors from the owner of the device
        client = gconf.client_get_default()
        color = XoColor(client.get_string('/desktop/sugar/user/color'))
        self.props.xo_color = color

        self.props.group = group

        self.mount = mount
        self.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                           [('journal-object-id', 0, 0)],
                           gtk.gdk.ACTION_COPY)
        self.connect('drag-data-received', self._drag_data_received_cb)

    def _drag_data_received_cb(self, widget, drag_context, x, y, selection_data,
                               info, timestamp):
        object_id = selection_data.data
        metadata = model.get(object_id)
        model.copy(metadata, self.mount.get_root().get_path())

