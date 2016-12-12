# Copyright (C) 2009, 2010 One Laptop per Child
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

import dbus
import uuid
from gi.repository import GObject

from jarabe.model import network
from jarabe.model.network import Settings
from jarabe.model.network import OlpcMesh as OlpcMeshSettings

_XS_ANYCAST = '\xc0\x27\xc0\x27\xc0\x00'


class OlpcMeshManager(object):

    def __init__(self, mesh_device):
        self._bus = dbus.SystemBus()

        # counter for how many asynchronous connection additions we are
        # waiting for
        self._add_connections_pending = 0

        self.mesh_device = mesh_device
        self.eth_device = self._get_companion_device()

        self._connection_queue = []
        """Stack of connections that we'll iterate through until we find one
           that works. Each entry in the list specifies the channel and
           whether to seek an XS or not."""

        # Ensure that all the connections we'll use later are present
        for channel in (1, 6, 11):
            self._ensure_connection_exists(channel, xs_hosted=True)
            self._ensure_connection_exists(channel, xs_hosted=False)

        props = dbus.Interface(self.mesh_device, dbus.PROPERTIES_IFACE)
        props.Get(network.NM_DEVICE_IFACE, 'State',
                  reply_handler=self.__get_mesh_state_reply_cb,
                  error_handler=self.__get_state_error_cb)

        props = dbus.Interface(self.eth_device, dbus.PROPERTIES_IFACE)
        props.Get(network.NM_DEVICE_IFACE, 'State',
                  reply_handler=self.__get_eth_state_reply_cb,
                  error_handler=self.__get_state_error_cb)

        self._bus.add_signal_receiver(self.__eth_device_state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self.eth_device.object_path,
                                      dbus_interface=network.NM_DEVICE_IFACE)

        self._bus.add_signal_receiver(self.__mshdev_state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self.mesh_device.object_path,
                                      dbus_interface=network.NM_DEVICE_IFACE)

        self._idle_source = 0
        self._mesh_device_state = network.NM_DEVICE_STATE_UNKNOWN
        self._eth_device_state = network.NM_DEVICE_STATE_UNKNOWN

        if self._add_connections_pending == 0:
            self.ready()

    def ready(self):
        """Called when all connections have been added (if they were not
        already present), meaning that we can start the automesh functionality.
        """
        if self._have_configured_connections():
            self._start_automesh_timer()
        else:
            self._start_automesh()

    def _get_companion_device(self):
        props = dbus.Interface(self.mesh_device, dbus.PROPERTIES_IFACE)
        eth_device_o = props.Get(network.NM_OLPC_MESH_IFACE, 'Companion')
        return self._bus.get_object(network.NM_SERVICE, eth_device_o)

    def _have_configured_connections(self):
        return len(network.get_connections().get_list()) > 0

    def _start_automesh_timer(self):
        """Start our timer system which basically looks for 10 seconds of
           inactivity on both devices, then starts automesh.

        """
        if self._idle_source != 0:
            GObject.source_remove(self._idle_source)
        self._idle_source = GObject.timeout_add_seconds(10, self._idle_check)

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

        if new_state >= network.NM_DEVICE_STATE_PREPARE \
                and new_state <= network.NM_DEVICE_STATE_ACTIVATED \
                and len(self._connection_queue) > 0:
            self._connection_queue = []

    def __mshdev_state_changed_cb(self, new_state, old_state, reason):
        self._mesh_device_state = new_state
        self._maybe_schedule_idle_check()

        if new_state == network.NM_DEVICE_STATE_FAILED:
            self._try_next_connection_from_queue()
        elif new_state == network.NM_DEVICE_STATE_ACTIVATED \
                and len(self._connection_queue) > 0:
            self._empty_connection_queue()

    def _maybe_schedule_idle_check(self):
        if self._mesh_device_state == network.NM_DEVICE_STATE_DISCONNECTED \
                and \
                self._eth_device_state == network.NM_DEVICE_STATE_DISCONNECTED:
            self._start_automesh_timer()

    def _idle_check(self):
        if self._mesh_device_state == network.NM_DEVICE_STATE_DISCONNECTED \
                and \
                self._eth_device_state == network.NM_DEVICE_STATE_DISCONNECTED:
            logging.debug('starting automesh due to inactivity')
            self._start_automesh()
        return False

    @staticmethod
    def _get_connection_id(channel, xs_hosted):
        if xs_hosted:
            return '%s%d' % (network.XS_MESH_CONNECTION_ID_PREFIX, channel)
        else:
            return '%s%d' % (network.MESH_CONNECTION_ID_PREFIX, channel)

    def _connection_added(self):
        if self._add_connections_pending > 0:
            self._add_connections_pending = self._add_connections_pending - 1
            if self._add_connections_pending == 0:
                self.ready()

    def _add_connection_reply_cb(self, connection):
        logging.debug("Added connection: %s", connection)
        self._connection_added()

    def _add_connection_err_cb(self, err):
        logging.debug("Error adding mesh connection: %s", err)
        self._connection_added()

    def _add_connection(self, channel, xs_hosted):
        anycast_addr = _XS_ANYCAST if xs_hosted else None
        wireless_config = OlpcMeshSettings(channel, anycast_addr)
        settings = Settings(wireless_cfg=wireless_config)
        if not xs_hosted:
            settings.ip4_config = network.IP4Config()
            settings.ip4_config.method = 'link-local'
        settings.connection.id = self._get_connection_id(channel, xs_hosted)
        settings.connection.autoconnect = False
        settings.connection.uuid = str(uuid.uuid4())
        settings.connection.type = '802-11-olpc-mesh'
        network.add_connection(settings,
                               reply_handler=self._add_connection_reply_cb,
                               error_handler=self._add_connection_err_cb)

    def _find_connection(self, channel, xs_hosted):
        connection_id = self._get_connection_id(channel, xs_hosted)
        return network.find_connection_by_id(connection_id)

    def _ensure_connection_exists(self, channel, xs_hosted):
        if not self._find_connection(channel, xs_hosted):
            self._add_connection(channel, xs_hosted)

    def _activate_connection(self, channel, xs_hosted):
        connection = self._find_connection(channel, xs_hosted)
        if connection:
            connection.activate(self.mesh_device.object_path)
        else:
            logging.warning("Could not find mesh connection")

    def _try_next_connection_from_queue(self):
        if len(self._connection_queue) == 0:
            return

        channel, xs_hosted = self._connection_queue.pop()
        self._activate_connection(channel, xs_hosted)

    def _empty_connection_queue(self):
        self._connection_queue = []

    def user_activate_channel(self, channel):
        """Activate a mesh connection on a user-specified channel.
        Looks for XS first, then resorts to simple mesh."""
        self._empty_connection_queue()
        self._connection_queue.append((channel, False))
        self._connection_queue.append((channel, True))
        self._try_next_connection_from_queue()

    def _start_automesh(self):
        """Start meshing automatically, intended when there are no better
        networks to connect to. First looks for XS on all channels, then falls
        back to simple mesh on channel 1."""
        self._empty_connection_queue()
        self._connection_queue.append((1, False))
        self._connection_queue.append((11, True))
        self._connection_queue.append((6, True))
        self._connection_queue.append((1, True))
        self._try_next_connection_from_queue()
