# Copyright (C) 2010 One Laptop per Child
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
from sugar.util import unique_id
from jarabe.model.network import IP4Config

_NM_SERVICE = 'org.freedesktop.NetworkManager'
_NM_IFACE = 'org.freedesktop.NetworkManager'
_NM_PATH = '/org/freedesktop/NetworkManager'
_NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
_NM_WIRELESS_IFACE = 'org.freedesktop.NetworkManager.Device.Wireless'
_NM_ACCESSPOINT_IFACE = 'org.freedesktop.NetworkManager.AccessPoint'
_NM_ACTIVE_CONN_IFACE = 'org.freedesktop.NetworkManager.Connection.Active'

_adhoc_manager_instance = None


def get_adhoc_manager_instance():
    global _adhoc_manager_instance
    if _adhoc_manager_instance is None:
        _adhoc_manager_instance = AdHocManager()
    return _adhoc_manager_instance


class AdHocManager(gobject.GObject):
    """To mimic the mesh behavior on devices where mesh hardware is
    not available we support the creation of an Ad-hoc network on
    three channels 1, 6, 11. If Sugar sees no "known" network when it
    starts, it does autoconnect to an Ad-hoc network.

    """

    __gsignals__ = {
        'members-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                            ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT])),
        'state-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                          ([gobject.TYPE_PYOBJECT, gobject.TYPE_PYOBJECT]))
    }

    _AUTOCONNECT_TIMEOUT = 30
    _CHANNEL_1 = 1
    _CHANNEL_6 = 6
    _CHANNEL_11 = 11

    def __init__(self):
        gobject.GObject.__init__(self)

        self._bus = dbus.SystemBus()
        self._device = None
        self._idle_source = 0
        self._listening_called = 0
        self._device_state = network.DEVICE_STATE_UNKNOWN

        self._current_channel = None
        self._networks = {self._CHANNEL_1: None,
                          self._CHANNEL_6: None,
                          self._CHANNEL_11: None}

    def start_listening(self, device):
        self._listening_called += 1
        if self._listening_called > 1:
            raise RuntimeError('The start listening method can' \
                                   ' only be called once.')

        self._device = device
        props = dbus.Interface(device, 'org.freedesktop.DBus.Properties')
        self._device_state = props.Get(_NM_DEVICE_IFACE, 'State')

        self._bus.add_signal_receiver(self.__device_state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)

        self._bus.add_signal_receiver(self.__wireless_properties_changed_cb,
                                      signal_name='PropertiesChanged',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_WIRELESS_IFACE)

    def stop_listening(self):
        self._bus.remove_signal_receiver(self.__device_state_changed_cb,
                                         signal_name='StateChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_DEVICE_IFACE)
        self._bus.remove_signal_receiver(self.__wireless_properties_changed_cb,
                                         signal_name='PropertiesChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_WIRELESS_IFACE)

    def __device_state_changed_cb(self, new_state, old_state, reason):
        self._device_state = new_state
        self._update_state()

    def __wireless_properties_changed_cb(self, properties):
        if 'ActiveAccessPoint' in properties and \
                properties['ActiveAccessPoint'] != '/':
            active_ap = self._bus.get_object(_NM_SERVICE,
                                             properties['ActiveAccessPoint'])
            props = dbus.Interface(active_ap, dbus.PROPERTIES_IFACE)
            props.GetAll(_NM_ACCESSPOINT_IFACE, byte_arrays=True,
                         reply_handler=self.__get_all_ap_props_reply_cb,
                         error_handler=self.__get_all_ap_props_error_cb)

    def __get_all_ap_props_reply_cb(self, properties):
        if properties['Mode'] == network.NM_802_11_MODE_ADHOC and \
                'Frequency' in properties:
            frequency = properties['Frequency']
            self._current_channel = network.frequency_to_channel(frequency)
        else:
            self._current_channel = None
        self._update_state()

    def __get_all_ap_props_error_cb(self, err):
        logging.error('Error getting the access point properties: %s', err)

    def _update_state(self):
        self.emit('state-changed', self._current_channel, self._device_state)

    def _have_configured_connections(self):
        return len(network.get_settings().connections) > 0

    def autoconnect(self):
        """Autoconnect to an Ad-hoc network"""
        if self._device_state != network.DEVICE_STATE_DISCONNECTED:
            return
        elif self._have_configured_connections():
            self._autoconnect_adhoc_timer()
        else:
            self._autoconnect_adhoc()

    def _autoconnect_adhoc_timer(self):
        """Start a timer which basically looks for 30 seconds of inactivity
        on the device, then does autoconnect to an Ad-hoc network.

        """
        if self._idle_source != 0:
            gobject.source_remove(self._idle_source)
        self._idle_source = gobject.timeout_add_seconds( \
                self._AUTOCONNECT_TIMEOUT, self.__idle_check_cb)

    def __idle_check_cb(self):
        if  self._device_state == network.DEVICE_STATE_DISCONNECTED:
            logging.debug("Connect to Ad-hoc network due to inactivity.")
            self._autoconnect_adhoc()
        return False

    def _autoconnect_adhoc(self):
        """First we try if there is an Ad-hoc network that is used by other
        learners in the area, if not we default to channel 1.

        """
        if self._networks[self._CHANNEL_1] is not None:
            self._connect(self._CHANNEL_1)
        elif self._networks[self._CHANNEL_6] is not None:
            self._connect(self._CHANNEL_6)
        elif self._networks[self._CHANNEL_11] is not None:
            self._connect(self._CHANNEL_11)
        else:
            self._connect(self._CHANNEL_1)

    def activate_channel(self, channel):
        """Activate a sugar Ad-hoc network.

        Keyword arguments:
        channel -- Channel to connect to (should be 1, 6, 11)

        """
        self._connect(channel)

    def _connect(self, channel):
        name = "Ad-hoc Network %d" % channel
        connection = network.find_connection_by_ssid(name)
        if connection is None:
            settings = Settings()
            settings.connection.id = name
            settings.connection.uuid = unique_id()
            settings.connection.type = '802-11-wireless'
            settings.wireless.ssid = dbus.ByteArray(name)
            settings.wireless.band = 'bg'
            settings.wireless.channel = channel
            settings.wireless.mode = 'adhoc'
            settings.ip4_config = IP4Config()
            settings.ip4_config.method = 'link-local'

            connection = network.add_connection(name, settings)

        obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
        netmgr = dbus.Interface(obj, _NM_IFACE)

        netmgr.ActivateConnection(network.SETTINGS_SERVICE,
                                  connection.path,
                                  self._device.object_path,
                                  '/',
                                  reply_handler=self.__activate_reply_cb,
                                  error_handler=self.__activate_error_cb)

    def deactivate_active_channel(self):
        """Deactivate the current active channel."""
        obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
        netmgr = dbus.Interface(obj, _NM_IFACE)

        netmgr_props = dbus.Interface(netmgr, dbus.PROPERTIES_IFACE)
        netmgr_props.Get(_NM_IFACE, 'ActiveConnections', \
                reply_handler=self.__get_active_connections_reply_cb,
                error_handler=self.__get_active_connections_error_cb)

    def __get_active_connections_reply_cb(self, active_connections_o):
        for connection_o in active_connections_o:
            obj = self._bus.get_object(_NM_IFACE, connection_o)
            props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            state = props.Get(_NM_ACTIVE_CONN_IFACE, 'State')
            if state == network.NM_ACTIVE_CONNECTION_STATE_ACTIVATED:
                access_point_o = props.Get(_NM_ACTIVE_CONN_IFACE,
                                           'SpecificObject')
                if access_point_o != '/':
                    obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
                    netmgr = dbus.Interface(obj, _NM_IFACE)
                    netmgr.DeactivateConnection(connection_o)

    def __get_active_connections_error_cb(self, err):
        logging.error('Error getting the active connections: %s', err)

    def __activate_reply_cb(self, connection):
        logging.debug('Ad-hoc network created: %s', connection)

    def __activate_error_cb(self, err):
        logging.error('Failed to create Ad-hoc network: %s', err)

    def add_access_point(self, access_point):
        """Add an access point to a network and notify the view to idicate
        the member change.

        Keyword arguments:
        access_point -- Access Point

        """
        if access_point.name.endswith(' 1'):
            self._networks[self._CHANNEL_1] = access_point
            self.emit('members-changed', self._CHANNEL_1, True)
        elif access_point.name.endswith(' 6'):
            self._networks[self._CHANNEL_6] = access_point
            self.emit('members-changed', self._CHANNEL_6, True)
        elif access_point.name.endswith('11'):
            self._networks[self._CHANNEL_11] = access_point
            self.emit('members-changed', self._CHANNEL_11, True)

    def is_sugar_adhoc_access_point(self, ap_object_path):
        """Checks whether an access point is part of a sugar Ad-hoc network.

        Keyword arguments:
        ap_object_path -- Access Point object path

        Return: Boolean

        """
        for access_point in self._networks.values():
            if access_point is not None:
                if access_point.model.object_path == ap_object_path:
                    return True
        return False

    def remove_access_point(self, ap_object_path):
        """Remove an access point from a sugar Ad-hoc network.

        Keyword arguments:
        ap_object_path -- Access Point object path

        """
        for channel in self._networks:
            if self._networks[channel] is not None:
                if self._networks[channel].model.object_path == ap_object_path:
                    self.emit('members-changed', channel, False)
                    self._networks[channel] = None
                    break
