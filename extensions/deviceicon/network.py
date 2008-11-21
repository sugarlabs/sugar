#
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

from gettext import gettext as _
import logging
import sha

import gtk
import gobject
import dbus

from sugar.graphics.icon import get_icon_state
from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar.graphics.toolbutton import ToolButton
from sugar.graphics import xocolor

from jarabe.model import network
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.view.pulsingicon import PulsingIcon

_ICON_NAME = 'network-wireless'

IP_ADDRESS_TEXT_TEMPLATE = _("IP address: %s")

_NM_SERVICE = 'org.freedesktop.NetworkManager'
_NM_IFACE = 'org.freedesktop.NetworkManager'
_NM_PATH = '/org/freedesktop/NetworkManager'
_NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
_NM_WIRELESS_IFACE = 'org.freedesktop.NetworkManager.Device.Wireless'
_NM_ACCESSPOINT_IFACE = 'org.freedesktop.NetworkManager.AccessPoint'
_NM_ACTIVE_CONN_IFACE = 'org.freedesktop.NetworkManager.Connection.Active'

_NM_DEVICE_STATE_UNKNOWN = 0
_NM_DEVICE_STATE_UNMANAGED = 1
_NM_DEVICE_STATE_UNAVAILABLE = 2
_NM_DEVICE_STATE_DISCONNECTED = 3
_NM_DEVICE_STATE_PREPARE = 4
_NM_DEVICE_STATE_CONFIG = 5
_NM_DEVICE_STATE_NEED_AUTH = 6
_NM_DEVICE_STATE_IP_CONFIG = 7
_NM_DEVICE_STATE_ACTIVATED = 8
_NM_DEVICE_STATE_FAILED = 9

def frequency_to_channel(frequency):
    ftoc = { 2412: 1, 2417: 2, 2422: 3, 2427: 4,
             2432: 5, 2437: 6, 2442: 7, 2447: 8,
             2452: 9, 2457: 10, 2462: 11, 2467: 12,
             2472: 13}
    return ftoc[frequency]

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

        self.set_disconnected()

    def set_connecting(self):
        self.props.secondary_text = _('Connecting...')

    def set_connected(self, frequency, iaddress):
        self.set_content(self._info)
        self.props.secondary_text = _('Connected')
        self._set_channel(frequency)
        self._set_ip_address(iaddress)
        self._disconnect_item.show()

    def set_disconnected(self):
        self.props.primary_text = ''
        self.props.secondary_text = _('Not connected')
        self.set_content(None)
        self._disconnect_item.hide()

    def __disconnect_activate_cb(self, menuitem):
        self.emit('deactivate-connection')

    def _inet_ntoa(self, iaddress):
        address = ['%s' % ((iaddress >> i) % 256) for i in [0, 8, 16, 24]]
        return ".".join(address)

    def _set_channel(self, frequency):
        try:
            channel = frequency_to_channel(frequency)
        except KeyError:
            channel = 0
        self._channel_label.set_text("%s: %d" % (_("Channel"), channel))

    def _set_ip_address(self, ip_address):
        if ip_address is not None:
            ip_address_text = IP_ADDRESS_TEXT_TEMPLATE % \
                self._inet_ntoa(ip_address)
        else:
            ip_address_text = ""
        self._ip_address_label.set_text(ip_address_text)


class WirelessDeviceView(ToolButton):

    FRAME_POSITION_RELATIVE = 300

    def __init__(self, device):
        ToolButton.__init__(self)

        self._bus = dbus.SystemBus()
        self._device = device
        self._flags = 0
        self._name = ''
        self._strength = 0
        self._frequency = 0
        self._device_state = None
        self._color = None
        self._active_ap_op = None

        self._icon = PulsingIcon()
        self._icon.props.icon_name = get_icon_state(_ICON_NAME, 0)
        self._inactive_color = xocolor.XoColor( \
            "%s,%s" % (style.COLOR_BUTTON_GREY.get_svg(),
                       style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulse_color = self._inactive_color
        self._icon.props.base_color = self._inactive_color

        self.set_icon_widget(self._icon)
        self._icon.show()

        self._palette = WirelessPalette(self._name)
        self._palette.connect('deactivate-connection', 
                              self.__deactivate_connection)  
        self.set_palette(self._palette)
        self._palette.props.invoker = FrameWidgetInvoker(self)
        self._palette.set_group_id('frame')

        self._device.Get(_NM_WIRELESS_IFACE, 'ActiveAccessPoint',
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
            props = dbus.Interface(active_ap, 'org.freedesktop.DBus.Properties')

            props.GetAll(_NM_ACCESSPOINT_IFACE, byte_arrays=True,
                         reply_handler=self.__get_all_props_reply_cb,
                         error_handler=self.__get_all_props_error_cb)

            self._bus.add_signal_receiver(self.__ap_properties_changed_cb,
                                          signal_name='PropertiesChanged',
                                          path=self._active_ap_op,
                                          dbus_interface=_NM_ACCESSPOINT_IFACE)

    def __get_active_ap_error_cb(self, err):
        logging.debug('Error getting the active access point: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._device_state = new_state
        self._update_state()

        self._device.Get(_NM_WIRELESS_IFACE, 'ActiveAccessPoint',
                         reply_handler=self.__get_active_ap_reply_cb,
                         error_handler=self.__get_active_ap_error_cb)

    def __ap_properties_changed_cb(self, properties):
        self._update_properties(properties)

    def _update_properties(self, properties):
        if 'Ssid' in properties:
            self._name = properties['Ssid']
        if 'Strength' in properties:
            self._strength = properties['Strength']
        if 'Flags' in properties:
            self._flags = properties['Flags']
        if 'Frequency' in properties:
            self._frequency = properties['Frequency']

        sh = sha.new()
        data = self._name + hex(self._flags)
        sh.update(data)
        h = hash(sh.digest())
        idx = h % len(xocolor.colors)

        self._color = xocolor.XoColor('%s,%s' % (xocolor.colors[idx][0],
                                                 xocolor.colors[idx][1]))
        self._update()

    def __get_all_props_reply_cb(self, properties):
        self._update_properties(properties)

    def __get_all_props_error_cb(self, err):
        logging.debug('Error getting the access point properties: %s', err)

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

        if state == network.DEVICE_STATE_ACTIVATED:
            icon_name = '%s-connected' % _ICON_NAME
        else:
            icon_name = _ICON_NAME

        icon_name = get_icon_state(icon_name, self._strength)
        if icon_name:
            self._icon.props.icon_name = icon_name

        if state == network.DEVICE_STATE_PREPARE or \
           state == network.DEVICE_STATE_CONFIG or \
           state == network.DEVICE_STATE_NEED_AUTH or \
           state == network.DEVICE_STATE_IP_CONFIG:
            self._palette.set_connecting()
            self._icon.props.pulsing = True
        elif state == network.DEVICE_STATE_ACTIVATED:
            props = dbus.Interface(self._device,
                                   'org.freedesktop.DBus.Properties')
            address = props.Get(_NM_DEVICE_IFACE, 'Ip4Address')
            self._palette.set_connected(self._frequency, address)
            self._icon.props.pulsing = False
        else:
            self._palette.set_disconnected()
            self._icon.props.pulsing = False
            self._icon.props.base_color = self._inactive_color
            self._icon.props.badge_name = None
            self._name = ''

    def _update_color(self):
        self._icon.props.base_color = self._color

    def __deactivate_connection(self, palette, data=None):
        if self._active_ap_op is not None:
            obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
            netmgr = dbus.Interface(obj, _NM_IFACE)
            netmgr_props = dbus.Interface(
                netmgr, 'org.freedesktop.DBus.Properties')
            active_connections_o = netmgr_props.Get(_NM_IFACE,
                                                    'ActiveConnections')

            for conn_o in active_connections_o:
                obj = self._bus.get_object(_NM_IFACE, conn_o)
                props = dbus.Interface(obj, 'org.freedesktop.DBus.Properties')
                ap_op = props.Get(_NM_ACTIVE_CONN_IFACE, 'SpecificObject')
                if ap_op == self._active_ap_op:
                    netmgr.DeactivateConnection(conn_o)
                    break

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
            logging.debug('%s service not available', _NM_SERVICE)
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
        props = dbus.Interface(nm_device, 'org.freedesktop.DBus.Properties')

        device_type = props.Get(_NM_DEVICE_IFACE, 'DeviceType')
        if device_type == network.DEVICE_TYPE_802_11_WIRELESS:
            device = WirelessDeviceView(nm_device)
            self._devices[device_op] = device
            self._tray.add_device(device)

    def __device_added_cb(self, device_op):
        self._check_device(device_op)

    def __device_removed_cb(self, device_op):
        if device_op in self._devices:
            device = self._devices[device_op]
            device.disconnect()
            self._tray.remove_device(device)
            del self._devices[device_op]

def setup(tray):
    device_observer = NetworkManagerObserver(tray)
