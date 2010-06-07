# Copyright (C) 2009-2010 One Laptop per Child
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

import dbus
import gobject

from jarabe.model import network
from jarabe.model.network import Settings
from jarabe.model.network import OlpcMesh as OlpcMeshSettings
from sugar.util import unique_id

_NM_SERVICE = 'org.freedesktop.NetworkManager'
_NM_IFACE = 'org.freedesktop.NetworkManager'
_NM_PATH = '/org/freedesktop/NetworkManager'
_NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
_NM_OLPC_MESH_IFACE = 'org.freedesktop.NetworkManager.Device.OlpcMesh'

_XS_ANYCAST = "\xc0\x27\xc0\x27\xc0\x00"

DEVICE_STATE_UNKNOWN = 0
DEVICE_STATE_UNMANAGED = 1
DEVICE_STATE_UNAVAILABLE = 2
DEVICE_STATE_DISCONNECTED = 3
DEVICE_STATE_PREPARE = 4
DEVICE_STATE_CONFIG = 5
DEVICE_STATE_NEED_AUTH = 6
DEVICE_STATE_IP_CONFIG = 7
DEVICE_STATE_ACTIVATED = 8
DEVICE_STATE_FAILED = 9

class OlpcMeshManager(object):
    def __init__(self, mesh_device):
        self._bus = dbus.SystemBus()

        self.mesh_device = mesh_device
        self.eth_device = self._get_companion_device()

        self._connection_queue = []
        """Stack of connections that we'll iterate through until we find one
           that works.

        """

        props = dbus.Interface(self.mesh_device,
                               'org.freedesktop.DBus.Properties')
        props.Get(_NM_DEVICE_IFACE, 'State',
                  reply_handler=self.__get_mesh_state_reply_cb,
                  error_handler=self.__get_state_error_cb)

        props = dbus.Interface(self.eth_device,
                               'org.freedesktop.DBus.Properties')
        props.Get(_NM_DEVICE_IFACE, 'State',
                  reply_handler=self.__get_eth_state_reply_cb,
                  error_handler=self.__get_state_error_cb)

        self._bus.add_signal_receiver(self.__eth_device_state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self.eth_device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)

        self._bus.add_signal_receiver(self.__mshdev_state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self.mesh_device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)

        self._idle_source = 0
        self._mesh_device_state = DEVICE_STATE_UNKNOWN
        self._eth_device_state = DEVICE_STATE_UNKNOWN

        if self._have_configured_connections():
            self._start_automesh_timer()
        else:
            self._start_automesh()

    def _get_companion_device(self):
        props = dbus.Interface(self.mesh_device,
                               'org.freedesktop.DBus.Properties')
        eth_device_o = props.Get(_NM_OLPC_MESH_IFACE, 'Companion')
        return self._bus.get_object(_NM_SERVICE, eth_device_o)

    def _have_configured_connections(self):
        return len(network.get_settings().connections) > 0

    def _start_automesh_timer(self):
        """Start our timer system which basically looks for 10 seconds of
           inactivity on both devices, then starts automesh.

        """
        if self._idle_source != 0:
            gobject.source_remove(self._idle_source)
        self._idle_source = gobject.timeout_add_seconds(10, self._idle_check)

    def __get_state_error_cb(self, err):
        logging.debug('Error getting the device state: %s', err)

    def __get_mesh_state_reply_cb(self, state):
        self._mesh_device_state = state
        self._maybe_schedule_idle_check()

    def __get_eth_state_reply_cb(self, state):
        self._eth_device_state = state
        self._maybe_schedule_idle_check()

    def __eth_device_state_changed_cb(self, new_state, old_state, reason):
        """If a connection is activated on the eth device, stop trying our
        automatic connections.

        """
        self._eth_device_state = new_state
        self._maybe_schedule_idle_check()

        if new_state >= DEVICE_STATE_PREPARE \
                and new_state <= DEVICE_STATE_ACTIVATED \
                and len(self._connection_queue) > 0:
            self._connection_queue = []

    def __mshdev_state_changed_cb(self, new_state, old_state, reason):
        self._mesh_device_state = new_state
        self._maybe_schedule_idle_check()

        if new_state == DEVICE_STATE_FAILED:
            self._try_next_connection_from_queue()
        elif new_state == DEVICE_STATE_ACTIVATED \
                and len(self._connection_queue) > 0:
            self._empty_connection_queue()

    def _maybe_schedule_idle_check(self):
        if self._mesh_device_state == DEVICE_STATE_DISCONNECTED \
                and self._eth_device_state == DEVICE_STATE_DISCONNECTED:
            self._start_automesh_timer()

    def _idle_check(self):
        if self._mesh_device_state == DEVICE_STATE_DISCONNECTED \
                and self._eth_device_state == DEVICE_STATE_DISCONNECTED:
            logging.debug("starting automesh due to inactivity")
            self._start_automesh()
        return False

    def _make_connection(self, channel, anycast_address=None):
        wireless_config = OlpcMeshSettings(channel, anycast_address)
        settings = Settings(wireless_cfg=wireless_config)
        if not anycast_address:
            settings.ip4_config = network.IP4Config()
            settings.ip4_config.method = 'link-local'
        settings.connection.id = 'olpc-mesh-' + str(channel)
        settings.connection.uuid = unique_id()
        settings.connection.type = '802-11-olpc-mesh'
        connection = network.add_connection(settings.connection.id, settings)
        return connection

    def __activate_reply_cb(self, connection):
        logging.debug('Connection activated: %s', connection)

    def __activate_error_cb(self, err):
        logging.error('Failed to activate connection: %s', err)

    def _activate_connection(self, channel, anycast_address=None):
        logging.debug("activate channel %d anycast %r",
                      channel, anycast_address)
        proxy = self._bus.get_object(_NM_SERVICE, _NM_PATH)
        network_manager = dbus.Interface(proxy, _NM_IFACE)
        connection = self._make_connection(channel, anycast_address)

        network_manager.ActivateConnection(network.SETTINGS_SERVICE,
                connection.path,
                self.mesh_device.object_path,
                self.mesh_device.object_path,
                reply_handler=self.__activate_reply_cb,
                error_handler=self.__activate_error_cb)

    def _try_next_connection_from_queue(self):
        if len(self._connection_queue) == 0:
            return

        channel, anycast = self._connection_queue.pop()
        self._activate_connection(channel, anycast)

    def _empty_connection_queue(self):
        self._connection_queue = []

    def user_activate_channel(self, channel):
        """Activate a mesh connection on a user-specified channel.
        Looks for XS first, then resorts to simple mesh."""
        self._empty_connection_queue()
        self._connection_queue.append((channel, None))
        self._connection_queue.append((channel, _XS_ANYCAST))
        self._try_next_connection_from_queue()

    def _start_automesh(self):
        """Start meshing automatically, intended when there are no better
        networks to connect to. First looks for XS on all channels, then falls
        back to simple mesh on channel 1."""
        self._empty_connection_queue()
        self._connection_queue.append((1, None))
        self._connection_queue.append((11, _XS_ANYCAST))
        self._connection_queue.append((6, _XS_ANYCAST))
        self._connection_queue.append((1, _XS_ANYCAST))
        self._try_next_connection_from_queue()

