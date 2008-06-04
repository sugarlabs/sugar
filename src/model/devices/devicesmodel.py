#
# Copyright (C) 2007, Red Hat, Inc.
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

from model.devices import device
from model.devices.network import wireless
from model.devices.network import mesh
from model.devices import battery
from model.devices import speaker
from hardware import hardwaremanager
from hardware import nmclient

class DevicesModel(gobject.GObject):
    __gsignals__ = {
        'device-appeared'   : (gobject.SIGNAL_RUN_FIRST,
                               gobject.TYPE_NONE, 
                              ([gobject.TYPE_PYOBJECT])),
        'device-disappeared': (gobject.SIGNAL_RUN_FIRST,
                               gobject.TYPE_NONE, 
                              ([gobject.TYPE_PYOBJECT]))
    }
   
    def __init__(self):
        gobject.GObject.__init__(self)

        self._devices = {}
        self._sigids = {}

        self._observe_hal_manager()
        self._observe_network_manager()

        try:
            self.add_device(speaker.Device())
        except Exception, speaker_fail_msg:
            logging.error("could not initialize speaker device: %s" %
                          speaker_fail_msg)

    def _observe_hal_manager(self):
        bus = dbus.Bus(dbus.Bus.TYPE_SYSTEM)
        proxy = bus.get_object('org.freedesktop.Hal',
                               '/org/freedesktop/Hal/Manager')
        hal_manager = dbus.Interface(proxy, 'org.freedesktop.Hal.Manager')

        for udi in hal_manager.FindDeviceByCapability('battery'):
            self.add_device(battery.Device(udi))

    def _observe_network_manager(self):
        network_manager = hardwaremanager.get_network_manager()
        if not network_manager:
            return

        for dev in network_manager.get_devices():
            self._check_network_device(dev)

        network_manager.connect('device-added',
                                self._network_device_added_cb)
        network_manager.connect('device-activating',
                                self._network_device_activating_cb)
        network_manager.connect('device-activated',
                                self._network_device_activated_cb)
        network_manager.connect('device-removed',
                                self._network_device_removed_cb)

    def _network_device_added_cb(self, network_manager, nm_device):
        state = nm_device.get_state()
        if state == nmclient.DEVICE_STATE_ACTIVATING \
                or state == nmclient.DEVICE_STATE_ACTIVATED:
            self._check_network_device(nm_device)

    def _network_device_activating_cb(self, network_manager, nm_device):
        self._check_network_device(nm_device)

    def _network_device_activated_cb(self, network_manager, nm_device):
        pass

    def _network_device_removed_cb(self, network_manager, nm_device):
        if self._devices.has_key(str(nm_device.get_op())):
            self.remove_device(self._get_network_device(nm_device))

    def _check_network_device(self, nm_device):
        if not nm_device.is_valid():
            logging.debug("Device %s not valid" % nm_device.get_op())
            return

        dtype = nm_device.get_type()
        if dtype == nmclient.DEVICE_TYPE_802_11_WIRELESS \
           or dtype == nmclient.DEVICE_TYPE_802_11_MESH_OLPC:
            self._add_network_device(nm_device)

    def _get_network_device(self, nm_device):
        return self._devices[str(nm_device.get_op())]

    def _network_device_state_changed_cb(self, dev, param):
        if dev.props.state == device.STATE_INACTIVE:
            self.remove_device(dev)

    def _add_network_device(self, nm_device):
        if self._devices.has_key(str(nm_device.get_op())):
            logging.debug("Tried to add device %s twice" % nm_device.get_op())
            return

        dtype = nm_device.get_type()
        if dtype == nmclient.DEVICE_TYPE_802_11_WIRELESS:
            dev = wireless.Device(nm_device)
            self.add_device(dev)
            sigid = dev.connect('notify::state',
                                self._network_device_state_changed_cb)
            self._sigids[dev] = sigid
        if dtype == nmclient.DEVICE_TYPE_802_11_MESH_OLPC:
            dev = mesh.Device(nm_device)
            self.add_device(dev)
            sigid = dev.connect('notify::state',
                                self._network_device_state_changed_cb)
            self._sigids[dev] = sigid

    def __iter__(self):
        return iter(self._devices.values())

    def add_device(self, dev):
        self._devices[dev.get_id()] = dev
        self.emit('device-appeared', dev)

    def remove_device(self, dev):
        self.emit('device-disappeared', self._devices[dev.get_id()])
        dev.disconnect(self._sigids[dev])
        del self._sigids[dev]
        del self._devices[dev.get_id()]
