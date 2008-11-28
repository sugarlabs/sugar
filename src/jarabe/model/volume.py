# Copyright (C) 2007-2008, One Laptop Per Child
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
import dbus

from sugar import profile

HAL_SERVICE_NAME = 'org.freedesktop.Hal'
HAL_MANAGER_PATH = '/org/freedesktop/Hal/Manager'
HAL_MANAGER_IFACE = 'org.freedesktop.Hal.Manager'
HAL_DEVICE_IFACE = 'org.freedesktop.Hal.Device'
HAL_VOLUME_IFACE = 'org.freedesktop.Hal.Device.Volume'

MOUNT_OPTION_UID = 500
MOUNT_OPTION_UMASK = 000

_volumes_manager = None

class VolumesManager(gobject.GObject):

    __gtype_name__ = 'VolumesManager'

    __gsignals__ = {
        'volume-added': (gobject.SIGNAL_RUN_FIRST,
                         gobject.TYPE_NONE,
                         ([object])),
        'volume-removed': (gobject.SIGNAL_RUN_FIRST,
                           gobject.TYPE_NONE,
                           ([object]))
    }

    def __init__(self):
        gobject.GObject.__init__(self)

        self._volumes = {}

        bus = dbus.SystemBus()
        proxy = bus.get_object(HAL_SERVICE_NAME, HAL_MANAGER_PATH)
        self._hal_manager = dbus.Interface(proxy, HAL_MANAGER_IFACE)
        self._hal_manager.connect_to_signal('DeviceAdded',
                                            self._hal_device_added_cb)

        for udi in self._hal_manager.FindDeviceByCapability('volume'):
            if self._is_device_relevant(udi):
                try:
                    self._add_hal_device(udi)
                except Exception, e:
                    logging.error('Exception when mounting device %r: %r' % \
                                  (udi, e))

    def get_volumes(self):
        return self._volumes.values()

    def _hal_device_added_cb(self, udi):
        bus = dbus.SystemBus()
        device_object = bus.get_object(HAL_SERVICE_NAME, udi)
        device = dbus.Interface(device_object, HAL_DEVICE_IFACE)
        if device.QueryCapability('volume'):
            logging.debug('VolumesManager._hal_device_added_cb: %r', udi)
            if self._is_device_relevant(udi):
                self._add_hal_device(udi)

    def _is_device_relevant(self, udi):
        bus = dbus.SystemBus()
        device_object = bus.get_object(HAL_SERVICE_NAME, udi)
        device = dbus.Interface(device_object, HAL_DEVICE_IFACE)

        # Ignore volumes without a filesystem.
        if device.GetProperty('volume.fsusage') != 'filesystem':
            return False

        return True
            
    def _add_hal_device(self, udi):
        logging.debug('VolumeToolbar._add_hal_device: %r' % udi)

        bus = dbus.SystemBus()
        device_object = bus.get_object(HAL_SERVICE_NAME, udi)
        device = dbus.Interface(device_object, HAL_DEVICE_IFACE)

        # listen to mount/unmount
        device.connect_to_signal('PropertyModified',
                lambda *args: self._hal_device_property_modified_cb(udi, *args))

        bus.add_signal_receiver(self._hal_device_removed_cb,
                                'DeviceRemoved', 
                                HAL_MANAGER_IFACE, HAL_SERVICE_NAME,
                                HAL_MANAGER_PATH, arg0=udi)

        if device.GetProperty('volume.is_mounted'):
            self._add_volume(udi)
            return
        
        label = device.GetProperty('volume.label')
        fs_type = device.GetProperty('volume.fstype')
        valid_options = device.GetProperty('volume.mount.valid_options')
        options = []

        if 'uid=' in valid_options:
            options.append('uid=%i' % MOUNT_OPTION_UID)

        if 'umask=' in valid_options:
            options.append('umask=%i' % MOUNT_OPTION_UMASK)

        if 'noatime' in valid_options:
            options.append('noatime')

        if 'utf8' in valid_options:
            options.append('utf8')

        if 'iocharset=' in valid_options:
            options.append('iocharset=utf8')

        mount_point = label
        if not mount_point:
            mount_point = device.GetProperty('volume.uuid')

        volume = dbus.Interface(device_object, HAL_VOLUME_IFACE)

        # Try 100 times to get a mount point
        mounted = False
        i = 0
        while not mounted:
            try:
                if i > 0:
                    volume.Mount('%s_%d' % (mount_point, i), fs_type, options)
                else:
                    volume.Mount(mount_point, fs_type, options)
                mounted = True
            except dbus.DBusException, e:
                s = 'org.freedesktop.Hal.Device.Volume.MountPointNotAvailable'
                if i < 100 and e.get_dbus_name() == s:
                    i += 1
                else:
                    raise

    def _hal_device_property_modified_cb(self, udi, count, changes):
        if 'volume.is_mounted' in [change[0] for change in changes]:
            logging.debug('VolumesManager._hal_device_property_modified: %r' % \
                          (udi))
            bus = dbus.SystemBus()
            #proxy = bus.get_object(HAL_SERVICE_NAME, HAL_MANAGER_PATH)
            #hal_manager = dbus.Interface(proxy, HAL_MANAGER_IFACE)
            # TODO: Why this doesn't work?
            #if not hal_manager.DeviceExists(udi):
            #    return

            proxy = bus.get_object(HAL_SERVICE_NAME, udi)
            device = dbus.Interface(proxy, HAL_DEVICE_IFACE)
            try:
                is_mounted = device.GetProperty('volume.is_mounted')
            except dbus.DBusException, e:
                logging.debug('e: %s' % e)
                return

            if is_mounted:
                if udi not in self._volumes:
                    self._add_volume(udi)
            else:
                if udi in self._volumes:
                    self._remove_volume(udi)

    def _add_volume(self, udi):
        logging.debug('_add_volume %r' % udi)
        bus = dbus.SystemBus()
        device_object = bus.get_object(HAL_SERVICE_NAME, udi)
        device = dbus.Interface(device_object, HAL_DEVICE_IFACE)

        volume_name = device.GetProperty('volume.label')
        if not volume_name:
            volume_name = device.GetProperty('volume.uuid')

        mount_point = device.GetProperty('volume.mount_point')

        storage_udi = device.GetProperty('block.storage_device')
        obj = bus.get_object(HAL_SERVICE_NAME, storage_udi)
        storage_device = dbus.Interface(obj, HAL_DEVICE_IFACE)
        can_eject = storage_device.GetProperty('storage.hotpluggable')

        volume = Volume(volume_name,
                        self._get_icon_for_volume(device),
                        profile.get_color(),
                        udi,
                        mount_point,
                        can_eject)
        self._volumes[udi] = volume

        logging.debug('mounted volume %s' % udi)
        self.emit('volume-added', volume)
        
    def _remove_volume(self, udi):
        volume = self._volumes[udi]
        del self._volumes[udi]
        self.emit('volume-removed', volume)

    def _hal_device_removed_cb(self, udi):
        logging.debug('VolumesManager._hal_device_removed_cb: %r', udi)
        if udi in self._volumes:
            self._remove_volume(udi)

    def _get_icon_for_volume(self, device):
        bus = dbus.SystemBus()
        storage_udi = device.GetProperty('block.storage_device')
        obj = bus.get_object(HAL_SERVICE_NAME, storage_udi)
        storage_device = dbus.Interface(obj, HAL_DEVICE_IFACE)

        storage_drive_type = storage_device.GetProperty('storage.drive_type')
        if storage_drive_type == 'sd_mmc':
            return 'media-flash-sd-mmc'
        elif device.GetProperty('volume.mount_point') == '/':
            return 'computer-xo'
        else:
            return 'media-flash-usb'

class Volume(object):
    def __init__(self, name, icon_name, icon_color, udi, mount_point,
                 can_eject):
        self.name = name
        self.icon_name = icon_name
        self.icon_color = icon_color
        self.udi = udi
        self.mount_point = mount_point
        self.can_eject = can_eject

    def unmount(self):
        logging.debug('Volumes.unmount: %r', self.udi)
        bus = dbus.SystemBus()
        device_object = bus.get_object(HAL_SERVICE_NAME, self.udi)
        volume = dbus.Interface(device_object, HAL_VOLUME_IFACE)
        volume.Unmount([])

def get_volumes_manager():
    global _volumes_manager
    if _volumes_manager is None:
        _volumes_manager = VolumesManager()
    return _volumes_manager

