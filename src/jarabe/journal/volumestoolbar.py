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
import gtk

from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.palette import Palette

from jarabe.model import volume
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
        self._volume_added_hid = None
        self._volume_removed_hid = None

        self.connect('destroy', self.__destroy_cb)

        gobject.idle_add(self._set_up_volumes)

    def __destroy_cb(self, widget):
        volumes_manager = volume.get_volumes_manager()
        volumes_manager.disconnect(self._volume_added_hid)
        volumes_manager.disconnect(self._volume_removed_hid)

    def _set_up_volumes(self):
        volumes_manager = volume.get_volumes_manager()
        self._volume_added_hid = \
                volumes_manager.connect('volume-added', self._volume_added_cb)
        self._volume_removed_hid = \
                volumes_manager.connect('volume-removed',
                                        self._volume_removed_cb)

        for vol in volumes_manager.get_volumes():
            self._add_button(vol)

    def _volume_added_cb(self, volumes_manager, vol):
        self._add_button(vol)

    def _volume_removed_cb(self, volumes_manager, vol):
        self._remove_button(vol)

    def _add_button(self, vol):
        logging.debug('VolumeToolbar._add_button: %r' % vol.name)

        if self._volume_buttons:
            group = self._volume_buttons[0]
        else:
            group = None

        palette = Palette(vol.name)

        button = VolumeButton(vol, group)
        button.set_palette(palette)
        button.connect('toggled', self._button_toggled_cb, vol)
        if self._volume_buttons:
            position = self.get_item_index(self._volume_buttons[-1]) + 1
        else:
            position = 0
        self.insert(button, position)
        button.show()

        self._volume_buttons.append(button)

        if vol.can_eject:
            menu_item = gtk.MenuItem(_('Unmount'))
            menu_item.connect('activate', self._unmount_activated_cb, vol)
            palette.menu.append(menu_item)
            menu_item.show()

        if len(self.get_children()) > 1:
            self.show()

    def _button_toggled_cb(self, button, vol):
        if button.props.active:
            self.emit('volume-changed', vol)

    def _unmount_activated_cb(self, menu_item, vol):
        logging.debug('VolumesToolbar._unmount_activated_cb: %r', vol.udi)
        vol.unmount()

    def _remove_button(self, vol):
        for button in self.get_children():
            if button.volume.udi == vol.udi:
                self._volume_buttons.remove(button)
                self.remove(button)
                self.get_children()[0].props.active = True
                
                if len(self.get_children()) < 2:
                    self.hide()
                return
        logging.error('Couldnt find volume with udi %r' % vol.udi)

    def set_active_volume(self, mount_point):
        for button in self.get_children():
            logging.error('udi %r' % button.volume.mount_point)
            if button.volume.mount_point == mount_point:
                button.props.active = True
                return
        logging.error('Couldnt find volume with mount_point %r' % mount_point)

class VolumeButton(RadioToolButton):
    def __init__(self, vol, group):
        RadioToolButton.__init__(self)
        self.props.named_icon = vol.icon_name
        self.props.xo_color = vol.icon_color
        self.props.group = group

        self.volume = vol
        self.drag_dest_set(gtk.DEST_DEFAULT_ALL,
                           [('journal-object-id', 0, 0)],
                           gtk.gdk.ACTION_COPY)
        self.connect('drag-data-received', self._drag_data_received_cb)

    def _drag_data_received_cb(self, widget, drag_context, x, y, selection_data,
                               info, timestamp):
        object_id = selection_data.data
        metadata = model.get(object_id)
        model.copy(metadata, self.volume.mount_point)

