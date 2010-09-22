#
# Copyright (C) 2008-2010 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009 Paraguay Educa, Martin Abente
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

from gettext import gettext as _
import logging
import sha
import socket
import struct
import re
import datetime
import time
import gtk
import gobject
import gconf
import dbus

from sugar.graphics.icon import get_icon_state
from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics.tray import TrayIcon
from sugar.graphics import xocolor
from sugar.util import unique_id
from sugar import profile

from jarabe.model import network
from jarabe.model.network import Settings
from jarabe.model.network import IP4Config
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.view.pulsingicon import PulsingIcon

IP_ADDRESS_TEXT_TEMPLATE = _("IP address: %s")

_NM_SERVICE = 'org.freedesktop.NetworkManager'
_NM_IFACE = 'org.freedesktop.NetworkManager'
_NM_PATH = '/org/freedesktop/NetworkManager'
_NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
_NM_WIRED_IFACE = 'org.freedesktop.NetworkManager.Device.Wired'
_NM_WIRELESS_IFACE = 'org.freedesktop.NetworkManager.Device.Wireless'
_NM_OLPC_MESH_IFACE = 'org.freedesktop.NetworkManager.Device.OlpcMesh'
_NM_SERIAL_IFACE = 'org.freedesktop.NetworkManager.Device.Serial'
_NM_ACCESSPOINT_IFACE = 'org.freedesktop.NetworkManager.AccessPoint'
_NM_ACTIVE_CONN_IFACE = 'org.freedesktop.NetworkManager.Connection.Active'

_GSM_STATE_NOT_READY = 0
_GSM_STATE_DISCONNECTED = 1
_GSM_STATE_CONNECTING = 2
_GSM_STATE_CONNECTED = 3
_GSM_STATE_NEED_AUTH = 4

class WirelessPalette(Palette):
    __gtype_name__ = 'SugarWirelessPalette'

    __gsignals__ = {
        'deactivate-connection' : (gobject.SIGNAL_RUN_FIRST,
                                   gobject.TYPE_NONE, ([]))
    }

    def __init__(self, primary_text):
        Palette.__init__(self, label=primary_text)

        self._disconnect_item = None

        self._channel_label = gtk.Label()
        self._channel_label.props.xalign = 0.0
        self._channel_label.show()

        self._ip_address_label = gtk.Label()

        self._info = gtk.VBox()

        def _padded(child, xalign=0, yalign=0.5):
            padder = gtk.Alignment(xalign=xalign, yalign=yalign,
                                   xscale=1, yscale=0.33)
            padder.set_padding(style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING)
            padder.add(child)
            return padder

        self._info.pack_start(_padded(self._channel_label))
        self._info.pack_start(_padded(self._ip_address_label))
        self._info.show_all()

        self._disconnect_item = gtk.MenuItem(_('Disconnect...'))
        self._disconnect_item.connect('activate', self.__disconnect_activate_cb)
        self.menu.append(self._disconnect_item)

    def set_connecting(self):
        self.props.secondary_text = _('Connecting...')

    def _set_connected(self, iaddress):
        self.set_content(self._info)
        self.props.secondary_text = _('Connected')
        self._set_ip_address(iaddress)
        self._disconnect_item.show()
        
    def set_connected_with_frequency(self, frequency, iaddress):
        self._set_connected(iaddress)
        self._set_frequency(frequency)

    def set_connected_with_channel(self, channel, iaddress):
        self._set_connected(iaddress)
        self._set_channel(channel)

    def set_disconnected(self):
        self.props.primary_text = ''
        self.props.secondary_text = ''
        self._disconnect_item.hide()
        self.set_content(None)

    def __disconnect_activate_cb(self, menuitem):
        self.emit('deactivate-connection')

    def _set_frequency(self, frequency):
        try:
            channel = network.frequency_to_channel(frequency)
        except KeyError:
            channel = 0
        self._set_channel(channel)

    def _set_channel(self, channel):
        self._channel_label.set_text("%s: %d" % (_("Channel"), channel))

    def _set_ip_address(self, ip_address):
        if ip_address is not None:
            ip_address_text = IP_ADDRESS_TEXT_TEMPLATE % \
                socket.inet_ntoa(struct.pack('I', ip_address))
        else:
            ip_address_text = ""
        self._ip_address_label.set_text(ip_address_text)


class WiredPalette(Palette):
    __gtype_name__ = 'SugarWiredPalette'

    def __init__(self):
        Palette.__init__(self, label=_('Wired Network'))

        self._speed_label = gtk.Label()
        self._speed_label.props.xalign = 0.0
        self._speed_label.show()

        self._ip_address_label = gtk.Label()

        self._info = gtk.VBox()

        def _padded(child, xalign=0, yalign=0.5):
            padder = gtk.Alignment(xalign=xalign, yalign=yalign,
                                   xscale=1, yscale=0.33)
            padder.set_padding(style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING)
            padder.add(child)
            return padder

        self._info.pack_start(_padded(self._speed_label))
        self._info.pack_start(_padded(self._ip_address_label))
        self._info.show_all()

        self.set_content(self._info)
        self.props.secondary_text = _('Connected')

    def set_connected(self, speed, iaddress):
        self._speed_label.set_text('%s: %d Mb/s' % (_('Speed'), speed))
        self._set_ip_address(iaddress)

    def _inet_ntoa(self, iaddress):
        address = ['%s' % ((iaddress >> i) % 256) for i in [0, 8, 16, 24]]
        return ".".join(address)

    def _set_ip_address(self, ip_address):
        if ip_address is not None:
            ip_address_text = IP_ADDRESS_TEXT_TEMPLATE % \
                socket.inet_ntoa(struct.pack('I', ip_address))
        else:
            ip_address_text = ""
        self._ip_address_label.set_text(ip_address_text)

class GsmPalette(Palette):
    __gtype_name__ = 'SugarGsmPalette'

    __gsignals__ = {
        'gsm-connect'         : (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([])),
        'gsm-disconnect'      : (gobject.SIGNAL_RUN_FIRST,
                                 gobject.TYPE_NONE, ([])),
    }

    def __init__(self):
        Palette.__init__(self, label=_('Wireless modem'))

        self._current_state = None

        self._toggle_state_item = gtk.MenuItem('')
        self._toggle_state_item.connect('activate', self.__toggle_state_cb)
        self.menu.append(self._toggle_state_item)
        self._toggle_state_item.show()

        self.set_gsm_state(_GSM_STATE_NOT_READY)

        self.info_box = gtk.VBox()

        self.data_label = gtk.Label()
        self.data_label.props.xalign = 0.0
        label_alignment = self._add_widget_with_padding(self.data_label)
        self.info_box.pack_start(label_alignment)
        self.data_label.show()
        label_alignment.show()

        self.connection_time_label = gtk.Label()
        self.connection_time_label.props.xalign = 0.0
        label_alignment = self._add_widget_with_padding( \
                self.connection_time_label)
        self.info_box.pack_start(label_alignment)
        self.connection_time_label.show()
        label_alignment.show()

        self.info_box.show()
        self.set_content(self.info_box)

    def _add_widget_with_padding(self, child, xalign=0, yalign=0.5):
        alignment = gtk.Alignment(xalign=xalign, yalign=yalign,
                                  xscale=1, yscale=0.33)
        alignment.set_padding(style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING)
        alignment.add(child)
        return alignment

    def set_gsm_state(self, state):
        self._current_state = state
        self._update_label_and_text()

    def _update_label_and_text(self):
        if self._current_state == _GSM_STATE_NOT_READY:
            self._toggle_state_item.get_child().set_label('...')
            self.props.secondary_text = _('Please wait...')

        elif self._current_state == _GSM_STATE_DISCONNECTED:
            self._toggle_state_item.get_child().set_label(_('Connect'))
            self.props.secondary_text = _('Disconnected')

        elif self._current_state == _GSM_STATE_CONNECTING:
            self._toggle_state_item.get_child().set_label(_('Cancel'))
            self.props.secondary_text = _('Connecting...')

        elif self._current_state == _GSM_STATE_CONNECTED:
            self._toggle_state_item.get_child().set_label(_('Disconnect'))
            self.props.secondary_text = _('Connected')
            
        elif self._current_state == _GSM_STATE_NEED_AUTH:
            self._toggle_state_item.get_child().set_label(_('Sim requires Pin/Puk'))
            self.props.secondary_text = _('Authentication Error')
            
        else:
            raise ValueError('Invalid GSM state while updating label and ' \
                             'text, %s' % str(self._current_state))

    def __toggle_state_cb(self, menuitem):
        if self._current_state == _GSM_STATE_NOT_READY:
            pass
        elif self._current_state == _GSM_STATE_DISCONNECTED:
            self.emit('gsm-connect')
        elif self._current_state == _GSM_STATE_CONNECTING:
            self.emit('gsm-disconnect')
        elif self._current_state == _GSM_STATE_CONNECTED:
            self.emit('gsm-disconnect')
        elif self._current_state == _GSM_STATE_NEED_AUTH:
            self.emit('gsm-disconnect')
        else:
            raise ValueError('Invalid GSM state while emitting signal, %s' % \
                             str(self._current_state))


class WirelessDeviceView(ToolButton):

    FRAME_POSITION_RELATIVE = 302

    def __init__(self, device):
        ToolButton.__init__(self)

        self._bus = dbus.SystemBus()
        self._device = device
        self._device_props = None
        self._flags = 0
        self._name = ''
        self._mode = network.NM_802_11_MODE_UNKNOWN
        self._strength = 0
        self._frequency = 0
        self._device_state = None
        self._color = None
        self._active_ap_op = None

        self._icon = PulsingIcon()
        self._icon.props.icon_name = get_icon_state('network-wireless', 0)
        self._inactive_color = xocolor.XoColor( \
            "%s,%s" % (style.COLOR_BUTTON_GREY.get_svg(),
                       style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulse_color = self._inactive_color
        self._icon.props.base_color = self._inactive_color

        self.set_icon_widget(self._icon)
        self._icon.show()

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self._palette = WirelessPalette(self._name)
        self._palette.connect('deactivate-connection',
                              self.__deactivate_connection_cb)
        self.set_palette(self._palette)
        self._palette.set_group_id('frame')

        self._device_props = dbus.Interface(self._device, dbus.PROPERTIES_IFACE)
        self._device_props.GetAll(_NM_DEVICE_IFACE, byte_arrays=True, 
                              reply_handler=self.__get_device_props_reply_cb,
                              error_handler=self.__get_device_props_error_cb)

        self._device_props.Get(_NM_WIRELESS_IFACE, 'ActiveAccessPoint',
                               reply_handler=self.__get_active_ap_reply_cb,
                               error_handler=self.__get_active_ap_error_cb)

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__state_changed_cb,
                                         signal_name='StateChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_DEVICE_IFACE)

    def __get_device_props_reply_cb(self, properties):
        if 'State' in properties:
            self._device_state = properties['State']
            self._update_state()

    def __get_device_props_error_cb(self, err):
        logging.error('Error getting the device properties: %s', err)

    def __get_active_ap_reply_cb(self, active_ap_op):
        if self._active_ap_op != active_ap_op:
            if self._active_ap_op is not None:
                self._bus.remove_signal_receiver(
                    self.__ap_properties_changed_cb,
                    signal_name='PropertiesChanged',
                    path=self._active_ap_op,
                    dbus_interface=_NM_ACCESSPOINT_IFACE)
            if active_ap_op == '/':
                self._active_ap_op = None
                return
            self._active_ap_op = active_ap_op
            active_ap = self._bus.get_object(_NM_SERVICE, active_ap_op)
            props = dbus.Interface(active_ap, dbus.PROPERTIES_IFACE)

            props.GetAll(_NM_ACCESSPOINT_IFACE, byte_arrays=True,
                         reply_handler=self.__get_all_ap_props_reply_cb,
                         error_handler=self.__get_all_ap_props_error_cb)

            self._bus.add_signal_receiver(self.__ap_properties_changed_cb,
                                          signal_name='PropertiesChanged',
                                          path=self._active_ap_op,
                                          dbus_interface=_NM_ACCESSPOINT_IFACE)

    def __get_active_ap_error_cb(self, err):
        logging.error('Error getting the active access point: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._device_state = new_state
        self._update_state()
        self._device_props.Get(_NM_WIRELESS_IFACE, 'ActiveAccessPoint',
                               reply_handler=self.__get_active_ap_reply_cb,
                               error_handler=self.__get_active_ap_error_cb)

    def __ap_properties_changed_cb(self, properties):
        self._update_properties(properties)

    def _update_properties(self, properties):
        if 'Mode' in properties:
            self._mode = properties['Mode']
            self._color = None
        if 'Ssid' in properties:
            self._name = properties['Ssid']
            self._color = None
        if 'Strength' in properties:
            self._strength = properties['Strength']
        if 'Flags' in properties:
            self._flags = properties['Flags']
        if 'Frequency' in properties:
            self._frequency = properties['Frequency']

        if self._color == None:
            if self._mode == network.NM_802_11_MODE_ADHOC and \
                    self._name.startswith('Ad-hoc Network'):
                self._color = profile.get_color()
            else:
                sh = sha.new()
                data = self._name + hex(self._flags)
                sh.update(data)
                h = hash(sh.digest())
                idx = h % len(xocolor.colors)

                self._color = xocolor.XoColor('%s,%s' %
                                              (xocolor.colors[idx][0],
                                               xocolor.colors[idx][1]))
        self._update()

    def __get_all_ap_props_reply_cb(self, properties):
        self._update_properties(properties)

    def __get_all_ap_props_error_cb(self, err):
        logging.error('Error getting the access point properties: %s', err)

    def _update(self):
        if self._flags == network.NM_802_11_AP_FLAGS_PRIVACY:
            self._icon.props.badge_name = "emblem-locked"
        else:
            self._icon.props.badge_name = None

        self._palette.props.primary_text = self._name

        self._update_state()
        self._update_color()

    def _update_state(self):
        if self._active_ap_op is not None:
            state = self._device_state
        else:
            state = network.DEVICE_STATE_UNKNOWN

        if self._mode != network.NM_802_11_MODE_ADHOC and \
                self._name.startswith('Ad-hoc Network') == False:
            if state == network.DEVICE_STATE_ACTIVATED:
                icon_name = '%s-connected' % 'network-wireless'
            else:
                icon_name = 'network-wireless'

            icon_name = get_icon_state(icon_name, self._strength)
            if icon_name:
                self._icon.props.icon_name = icon_name
        else:
            try:
                channel = network.frequency_to_channel(self._frequency)
            except KeyError:
                channel = 1
            if state == network.DEVICE_STATE_ACTIVATED:
                self._icon.props.icon_name = 'network-adhoc-%s-connected' \
                        % channel
            else:
                self._icon.props.icon_name = 'network-adhoc-%s' % channel
            self._icon.props.base_color = profile.get_color()

        if state == network.DEVICE_STATE_PREPARE or \
           state == network.DEVICE_STATE_CONFIG or \
           state == network.DEVICE_STATE_NEED_AUTH or \
           state == network.DEVICE_STATE_IP_CONFIG:
            self._palette.set_connecting()
            self._icon.props.pulsing = True
        elif state == network.DEVICE_STATE_ACTIVATED:
            address = self._device_props.Get(_NM_DEVICE_IFACE, 'Ip4Address')
            self._palette.set_connected_with_frequency(self._frequency,
                                                       address)
            self._icon.props.pulsing = False
        else:
            self._icon.props.badge_name = None
            self._icon.props.pulsing = False
            self._icon.props.pulse_color = self._inactive_color
            self._icon.props.base_color = self._inactive_color
            self._palette.set_disconnected()

    def _update_color(self):
        self._icon.props.base_color = self._color

    def __deactivate_connection_cb(self, palette, data=None):
        connection = network.find_connection_by_ssid(self._name)
        if connection:
            if self._mode == network.NM_802_11_MODE_INFRA:
                connection.set_disconnected()

        if self._active_ap_op is not None:
            obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
            netmgr = dbus.Interface(obj, _NM_IFACE)
            netmgr_props = dbus.Interface(netmgr, dbus.PROPERTIES_IFACE)
            active_connections_o = netmgr_props.Get(_NM_IFACE,
                                                    'ActiveConnections')

            for conn_o in active_connections_o:
                obj = self._bus.get_object(_NM_IFACE, conn_o)
                props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
                ap_op = props.Get(_NM_ACTIVE_CONN_IFACE, 'SpecificObject')
                if ap_op == self._active_ap_op:
                    netmgr.DeactivateConnection(conn_o)
                    break

    def __activate_reply_cb(self, connection):
        logging.debug('Network created: %s', connection)

    def __activate_error_cb(self, err):
        logging.debug('Failed to create network: %s', err)

class OlpcMeshDeviceView(ToolButton):
    _ICON_NAME = 'network-mesh'
    FRAME_POSITION_RELATIVE = 302

    def __init__(self, device, state):
        ToolButton.__init__(self)

        self._bus = dbus.SystemBus()
        self._device = device
        self._device_props = None
        self._device_state = None
        self._channel = 0

        self._icon = PulsingIcon(icon_name=self._ICON_NAME)
        self._inactive_color = xocolor.XoColor( \
            "%s,%s" % (style.COLOR_BUTTON_GREY.get_svg(),
                       style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulse_color = profile.get_color()
        self._icon.props.base_color = self._inactive_color

        self.set_icon_widget(self._icon)
        self._icon.show()

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self._palette = WirelessPalette(_("Mesh Network"))
        self._palette.connect('deactivate-connection',
                              self.__deactivate_connection)
        self.set_palette(self._palette)
        self._palette.set_group_id('frame')

        self.update_state(state)

        self._device_props = dbus.Interface(self._device,
                                            'org.freedesktop.DBus.Properties')
        self._device_props.Get(_NM_OLPC_MESH_IFACE, 'ActiveChannel',
                            reply_handler=self.__get_active_channel_reply_cb,
                            error_handler=self.__get_active_channel_error_cb)

        self._bus.add_signal_receiver(self.__wireless_properties_changed_cb,
                                      signal_name='PropertiesChanged',
                                      path=device.object_path,
                                      dbus_interface=_NM_OLPC_MESH_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__wireless_properties_changed_cb,
                                         signal_name='PropertiesChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_OLPC_MESH_IFACE)

    def __get_active_channel_reply_cb(self, channel):
        self._channel = channel
        self._update_text()

    def __get_active_channel_error_cb(self, err):
        logging.error('Error getting the active channel: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._device_state = new_state
        self._update()

    def __wireless_properties_changed_cb(self, properties):
        if 'ActiveChannel' in properties:
            self._channel = properties['ActiveChannel']
            self._update_text()

    def _update_text(self):
        text = _("Mesh Network") + " " + str(self._channel)
        self._palette.props.primary_text = text

    def _update(self):
        state = self._device_state

        if state in [network.DEVICE_STATE_PREPARE,
                     network.DEVICE_STATE_CONFIG,
                     network.DEVICE_STATE_NEED_AUTH,
                     network.DEVICE_STATE_IP_CONFIG]:
            self._icon.props.base_color = self._inactive_color
            self._icon.props.pulse_color = profile.get_color()
            self._palette.set_connecting()
            self._icon.props.pulsing = True
        elif state == network.DEVICE_STATE_ACTIVATED:
            address = self._device_props.Get(_NM_DEVICE_IFACE, 'Ip4Address')
            self._palette.set_connected_with_channel(self._channel, address)
            self._icon.props.base_color = profile.get_color()
            self._icon.props.pulsing = False
        self._update_text()

    def update_state(self, state):
        self._device_state = state
        self._update()

    def __deactivate_connection(self, palette, data=None):
        obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
        netmgr = dbus.Interface(obj, _NM_IFACE)
        netmgr_props = dbus.Interface(netmgr, 'org.freedesktop.DBus.Properties')
        active_connections_o = netmgr_props.Get(_NM_IFACE,
                                                'ActiveConnections')

        for conn_o in active_connections_o:
            # The connection path for a mesh connection is the device itself.
            obj = self._bus.get_object(_NM_IFACE, conn_o)
            props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
            ap_op = props.Get(_NM_ACTIVE_CONN_IFACE, 'SpecificObject')

            try:
                obj = self._bus.get_object(_NM_IFACE, ap_op)
                props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                type = props.Get(_NM_DEVICE_IFACE, 'DeviceType')
                if type == network.DEVICE_TYPE_802_11_OLPC_MESH:
                    netmgr.DeactivateConnection(conn_o)
                    break
            except dbus.exceptions.DBusException:
                pass

class WiredDeviceView(TrayIcon):

    _ICON_NAME = 'network-wired'
    FRAME_POSITION_RELATIVE = 301

    def __init__(self, speed, address):
        client = gconf.client_get_default()
        color = xocolor.XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=self._ICON_NAME, xo_color=color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self._palette = WiredPalette()
        self.set_palette(self._palette)
        self._palette.set_group_id('frame')
        self._palette.set_connected(speed, address)


class GsmDeviceView(TrayIcon):

    _ICON_NAME = 'network-gsm'
    FRAME_POSITION_RELATIVE = 303

    def __init__(self, device):
        self._connection_time_handler = None
        self._connection_timestamp = 0

        client = gconf.client_get_default()
        color = xocolor.XoColor(client.get_string('/desktop/sugar/user/color'))

        TrayIcon.__init__(self, icon_name=self._ICON_NAME, xo_color=color)

        self._bus = dbus.SystemBus()
        self._device = device

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self._palette = self._create_gsm_palette()
        self.set_palette(self._palette)

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)
        self._bus.add_signal_receiver(self.__ppp_stats_changed_cb,
                                      signal_name='PppStats',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_SERIAL_IFACE)

    def _create_gsm_palette(self):
        palette = GsmPalette()

        palette.set_group_id('frame')
        palette.connect('gsm-connect', self.__gsm_connect_cb)
        palette.connect('gsm-disconnect', self.__gsm_disconnect_cb)

        props = dbus.Interface(self._device, 'org.freedesktop.DBus.Properties')
        props.GetAll(_NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__current_state_check_cb,
                     error_handler=self.__current_state_check_error_cb)

        return palette

    def __gsm_connect_cb(self, palette, data=None):
        connection = network.find_gsm_connection()
        if connection is not None:
            obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
            netmgr = dbus.Interface(obj, _NM_IFACE)
            netmgr.ActivateConnection(network.SETTINGS_SERVICE,
                                        connection.path,
                                        self._device.object_path,
                                        '/',
                                        reply_handler=self.__connect_cb,
                                        error_handler=self.__connect_error_cb)

    def __connect_cb(self, active_connection):
        logging.debug('Connected successfully to gsm device, %s',
                      active_connection)

    def __connect_error_cb(self, error):
        raise RuntimeError('Error when connecting to gsm device, %s' % error)

    def __gsm_disconnect_cb(self, palette, data=None):
        obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
        netmgr = dbus.Interface(obj, _NM_IFACE)
        netmgr_props = dbus.Interface(netmgr, 'org.freedesktop.DBus.Properties')
        active_connections_o = netmgr_props.Get(_NM_IFACE, 'ActiveConnections')

        for conn_o in active_connections_o:
            obj = self._bus.get_object(_NM_IFACE, conn_o)
            props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
            devices = props.Get(_NM_ACTIVE_CONN_IFACE, 'Devices')
            if self._device.object_path in devices:
                netmgr.DeactivateConnection(
                        conn_o,
                        reply_handler=self.__disconnect_cb,
                        error_handler=self.__disconnect_error_cb)
                break

    def __disconnect_cb(self):
        logging.debug('Disconnected successfully gsm device')

    def __disconnect_error_cb(self, error):
        raise RuntimeError('Error when disconnecting gsm device, %s' % error)

    def __state_changed_cb(self, new_state, old_state, reason):
        logging.debug('GSM State: %s to %s, reason %s', old_state, new_state, reason)
        self._update_state(int(new_state))

    def __current_state_check_cb(self, properties):
        self._update_state(int(properties['State']))

    def __current_state_check_error_cb(self, error):
        raise RuntimeError('Error when checking gsm device state, %s' % error)

    def _update_state(self, state):
        gsm_state = None

        if state == network.DEVICE_STATE_ACTIVATED:
            gsm_state = _GSM_STATE_CONNECTED
            connection = network.find_gsm_connection()
            if connection is not None:
                connection.set_connected()
                self._connection_timestamp =  time.time() - \
                        connection.get_settings().connection.timestamp
                self._connection_time_handler = gobject.timeout_add( \
                        1000, self.__connection_timecount_cb)
                self._update_stats(0, 0)
                self._update_connection_time()                
                self._palette.info_box.show() 

        if state == network.DEVICE_STATE_DISCONNECTED:
            gsm_state = _GSM_STATE_DISCONNECTED
            self._connection_timestamp = 0
            if self._connection_time_handler is not None:
                gobject.source_remove(self._connection_time_handler)
            self._palette.info_box.hide() 

        elif state in [network.DEVICE_STATE_UNMANAGED,
                       network.DEVICE_STATE_UNAVAILABLE,
                       network.DEVICE_STATE_UNKNOWN]:
            gsm_state = _GSM_STATE_NOT_READY

        elif state in [network.DEVICE_STATE_PREPARE,
                       network.DEVICE_STATE_CONFIG,
                       network.DEVICE_STATE_IP_CONFIG]:
            gsm_state = _GSM_STATE_CONNECTING
            
        elif state in [network.DEVICE_STATE_NEED_AUTH]:
            gsm_state = _GSM_STATE_NEED_AUTH
            
        if self._palette is not None:
            self._palette.set_gsm_state(gsm_state)

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__state_changed_cb,
                                         signal_name='StateChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_DEVICE_IFACE)

    def __ppp_stats_changed_cb(self, in_bytes, out_bytes):
        self._update_stats(in_bytes, out_bytes)

    def _update_stats(self, in_bytes, out_bytes):
        in_kbytes = in_bytes / 1024
        out_kbytes = out_bytes / 1024
        text = _("Data sent %d kb / received %d kb") % (out_kbytes, in_kbytes)
        self._palette.data_label.set_text(text)

    def __connection_timecount_cb(self):
        self._connection_timestamp = self._connection_timestamp + 1
        self._update_connection_time()
        return True

    def _update_connection_time(self):
        connection_time = datetime.datetime.fromtimestamp( \
                self._connection_timestamp)
        text = _("Connection time ") + connection_time.strftime('%H : %M : %S')
        self._palette.connection_time_label.set_text(text)

class WirelessDeviceObserver(object):
    def __init__(self, device, tray):
        self._device = device
        self._device_view = None
        self._tray = tray
        self._device_view = WirelessDeviceView(self._device)
        self._tray.add_device(self._device_view)

    def disconnect(self):
        self._device_view.disconnect()
        self._tray.remove_device(self._device_view)
        del self._device_view
        self._device_view = None


class MeshDeviceObserver(object):
    def __init__(self, device, tray):
        self._bus = dbus.SystemBus()
        self._device = device
        self._device_view = None
        self._tray = tray

        props = dbus.Interface(self._device, dbus.PROPERTIES_IFACE)
        props.GetAll(_NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__get_device_props_reply_cb,
                     error_handler=self.__get_device_props_error_cb)

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)

    def _remove_device_view(self):
        self._device_view.disconnect()
        self._tray.remove_device(self._device_view)
        self._device_view = None


 
    def disconnect(self):
        if self._device_view is not None:
            self._remove_device_view()

        self._bus.remove_signal_receiver(self.__state_changed_cb,
                                         signal_name='StateChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_DEVICE_IFACE)

    def __get_device_props_reply_cb(self, properties):
        if 'State' in properties:
            self._update_state(properties['State'])

    def __get_device_props_error_cb(self, err):
        logging.error('Error getting the device properties: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._update_state(new_state)

    def _update_state(self, state):
        if state in (network.DEVICE_STATE_PREPARE, network.DEVICE_STATE_CONFIG,
                     network.DEVICE_STATE_NEED_AUTH,
                     network.DEVICE_STATE_IP_CONFIG,
                     network.DEVICE_STATE_ACTIVATED):
            if self._device_view is not None:
                self._device_view.update_state(state)
                return

            self._device_view = OlpcMeshDeviceView(self._device, state)
            self._tray.add_device(self._device_view)
        else:
            if self._device_view is not None:
                self._remove_device_view()


class WiredDeviceObserver(object):
    def __init__(self, device, tray):
        self._bus = dbus.SystemBus()
        self._device = device
        self._device_state = None
        self._device_view = None
        self._tray = tray

        props = dbus.Interface(self._device, dbus.PROPERTIES_IFACE)
        props.GetAll(_NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__get_device_props_reply_cb,
                     error_handler=self.__get_device_props_error_cb)

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__state_changed_cb,
                                         signal_name='StateChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_DEVICE_IFACE)

    def __get_device_props_reply_cb(self, properties):
        if 'State' in properties:
            self._update_state(properties['State'])

    def __get_device_props_error_cb(self, err):
        logging.error('Error getting the device properties: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._update_state(new_state)

    def _update_state(self, state):
        if state == network.DEVICE_STATE_ACTIVATED:
            props = dbus.Interface(self._device, dbus.PROPERTIES_IFACE)
            address = props.Get(_NM_DEVICE_IFACE, 'Ip4Address')
            speed = props.Get(_NM_WIRED_IFACE, 'Speed')
            self._device_view = WiredDeviceView(speed, address)
            self._tray.add_device(self._device_view)
        else:
            if self._device_view is not None:
                self._tray.remove_device(self._device_view)
                del self._device_view
                self._device_view = None

class GsmDeviceObserver(object):
    def __init__(self, device, tray):
        self._device = device
        self._device_view = None
        self._tray = tray

        self._device_view = GsmDeviceView(device)
        self._tray.add_device(self._device_view)

    def disconnect(self):
        self._device_view.disconnect()
        self._tray.remove_device(self._device_view)
        self._device_view = None

class NetworkManagerObserver(object):
    def __init__(self, tray):
        self._bus = dbus.SystemBus()
        self._devices = {}
        self._netmgr = None
        self._tray = tray

        try:
            obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
            self._netmgr = dbus.Interface(obj, _NM_IFACE)
        except dbus.DBusException:
            logging.error('%s service not available', _NM_SERVICE)
            return

        self._netmgr.GetDevices(reply_handler=self.__get_devices_reply_cb,
                                error_handler=self.__get_devices_error_cb)

        self._bus.add_signal_receiver(self.__device_added_cb,
                                      signal_name='DeviceAdded',
                                      dbus_interface=_NM_IFACE)
        self._bus.add_signal_receiver(self.__device_removed_cb,
                                      signal_name='DeviceRemoved',
                                      dbus_interface=_NM_IFACE)

    def __get_devices_reply_cb(self, devices):
        for device_op in devices:
            self._check_device(device_op)

    def __get_devices_error_cb(self, err):
        logging.error('Failed to get devices: %s', err)

    def _check_device(self, device_op):
        nm_device = self._bus.get_object(_NM_SERVICE, device_op)
        props = dbus.Interface(nm_device, dbus.PROPERTIES_IFACE)

        device_type = props.Get(_NM_DEVICE_IFACE, 'DeviceType')
        if device_type == network.DEVICE_TYPE_802_3_ETHERNET:
            device = WiredDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device
        elif device_type == network.DEVICE_TYPE_802_11_WIRELESS:
            device = WirelessDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device
        elif device_type == network.DEVICE_TYPE_802_11_OLPC_MESH:
            device = MeshDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device
        elif device_type == network.DEVICE_TYPE_GSM_MODEM:
            device = GsmDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device

    def __device_added_cb(self, device_op):
        self._check_device(device_op)

    def __device_removed_cb(self, device_op):
        if device_op in self._devices:
            device = self._devices[device_op]
            device.disconnect()
            del self._devices[device_op]

def setup(tray):
    device_observer = NetworkManagerObserver(tray)
