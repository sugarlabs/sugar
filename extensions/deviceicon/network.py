#
# Copyright (C) 2008 One Laptop Per Child
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009 Paraguay Educa, Martin Abente
# Copyright (C) 2010 Plan Ceibal, Daniel Castelo
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

from functools import partial
from gettext import gettext as _
import logging
import hashlib
import datetime
import time
from gi.repository import Gtk
from gi.repository import GObject
import dbus

from sugar3.graphics.icon import get_icon_state
from sugar3.graphics import style
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuItem
from sugar3.graphics.palettemenu import PaletteMenuItemSeparator
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.tray import TrayIcon
from sugar3.graphics.icon import Icon
from sugar3.graphics import xocolor
from sugar3 import profile

from jarabe.model import network
from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.view.pulsingicon import PulsingIcon


IP_ADDRESS_TEXT_TEMPLATE = _('IP address: %s')

_GSM_STATE_NOT_READY = 0
_GSM_STATE_DISCONNECTED = 1
_GSM_STATE_CONNECTING = 2
_GSM_STATE_CONNECTED = 3
_GSM_STATE_FAILED = 4


def _get_address_data_cb(ip_cb, address):
    ip_cb(address[0]['address'])

def _get_ip4_config_cb(bus, ip_cb, ip4_config):
    obj = bus.get_object(network.NM_SERVICE, ip4_config)
    props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
    props.Get('org.freedesktop.NetworkManager.IP4Config',
              'AddressData',
              reply_handler=partial(_get_address_data_cb, ip_cb),
              error_handler=logging.error)

def _get_ip(bus, props, ip_cb):
    props.Get(network.NM_DEVICE_IFACE, 'Ip4Config',
              reply_handler=partial(_get_ip4_config_cb, bus, ip_cb),
              error_handler=logging.error)


class WirelessPalette(Palette):
    __gtype_name__ = 'SugarWirelessPalette'

    __gsignals__ = {
        'deactivate-connection': (GObject.SignalFlags.RUN_FIRST, None,
                                  ([])),
    }

    def __init__(self, primary_text):
        Palette.__init__(self, label=primary_text)

        self._disconnect_item = None

        self._channel_label = Gtk.Label()
        self._channel_label.props.xalign = 0.0
        self._channel_label.show()

        self._ip_address_label = Gtk.Label()
        self._ip_address_label.props.xalign = 0.0
        self._ip_address_label.show()

        self._info = Gtk.VBox()

        self._disconnect_item = PaletteMenuItem(_('Disconnect'))
        icon = Icon(pixel_size=style.SMALL_ICON_SIZE,
                    icon_name='media-eject')
        self._disconnect_item.set_image(icon)
        self._disconnect_item.connect('activate',
                                      self.__disconnect_activate_cb)
        self._info.add(self._disconnect_item)

        separator = PaletteMenuItemSeparator()
        self._info.pack_start(separator, True, True, 0)

        def _padded(child, xalign=0, yalign=0.5):
            padder = Gtk.Alignment.new(xalign=xalign, yalign=yalign,
                                       xscale=1, yscale=0.33)
            padder.set_padding(style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING)
            padder.add(child)
            return padder

        self._info.pack_start(_padded(self._channel_label), True, True, 0)
        self._info.pack_start(_padded(self._ip_address_label), True, True, 0)
        self._info.show_all()

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
        self.props.primary_text = _('No wireless connection')
        self.props.secondary_text = ''
        self._disconnect_item.hide()
        self.set_content(None)

    def __disconnect_activate_cb(self, menuitem):
        self.emit('deactivate-connection')

    def _set_frequency(self, frequency):
        channel = network.frequency_to_channel(frequency)
        self._set_channel(channel)

    def _set_channel(self, channel):
        if channel == 0:
            self._channel_label.set_text('%s: %s' % (_('Channel'),
                                                     _('Unknown')))
        else:
            self._channel_label.set_text('%s: %d' % (_('Channel'),
                                                     channel))

    def _set_ip_address(self, ip_address):
        if ip_address is not None:
            ip_address_text = IP_ADDRESS_TEXT_TEMPLATE % ip_address
        else:
            ip_address_text = ""
        self._ip_address_label.set_text(ip_address_text)


class WiredPalette(Palette):
    __gtype_name__ = 'SugarWiredPalette'

    def __init__(self):
        Palette.__init__(self, primary_text=_('Wired Network'))

        self._speed_label = Gtk.Label()
        self._speed_label.props.xalign = 0.0
        self._speed_label.show()

        self._ip_address_label = Gtk.Label()

        self._info = Gtk.VBox()

        def _padded(child, xalign=0, yalign=0.5):
            padder = Gtk.Alignment.new(xalign=xalign, yalign=yalign,
                                       xscale=1, yscale=0.33)
            padder.set_padding(style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING,
                               style.DEFAULT_SPACING)
            padder.add(child)
            return padder

        self._info.pack_start(_padded(self._speed_label), True, True, 0)
        self._info.pack_start(_padded(self._ip_address_label), True, True, 0)
        self._info.show_all()

        self.set_content(self._info)
        self.props.secondary_text = _('Connected')

    def set_connected(self, speed, iaddress):
        self._speed_label.set_text('%s: %d Mb/s' % (_('Speed'), speed))
        self._set_ip_address(iaddress)

    def _inet_ntoa(self, iaddress):
        address = ['%s' % ((iaddress >> i) % 256) for i in [0, 8, 16, 24]]
        return '.'.join(address)

    def _set_ip_address(self, ip_address):
        if ip_address is not None:
            ip_address_text = IP_ADDRESS_TEXT_TEMPLATE % ip_address
        else:
            ip_address_text = ""
        self._ip_address_label.set_text(ip_address_text)


class GsmPalette(Palette):
    __gtype_name__ = 'SugarGsmPalette'

    __gsignals__ = {
        'gsm-connect': (GObject.SignalFlags.RUN_FIRST, None, ([])),
        'gsm-disconnect': (GObject.SignalFlags.RUN_FIRST, None, ([])),
    }

    def __init__(self):
        Palette.__init__(self, primary_text=_('Wireless modem'))

        self._current_state = None
        self._failed_connection = False

        self.info_box = Gtk.VBox()

        self._toggle_state_item = PaletteMenuItem('')
        self._toggle_state_item.connect('activate', self.__toggle_state_cb)
        self.info_box.pack_start(self._toggle_state_item, True, True, 0)
        self._toggle_state_item.show()

        self.error_title_label = Gtk.Label(label="")
        self.error_title_label.set_alignment(0, 0.5)
        self.error_title_label.set_line_wrap(True)
        self.info_box.pack_start(self.error_title_label, True, True, 0)
        self.error_description_label = Gtk.Label(label="")
        self.error_description_label.set_alignment(0, 0.5)
        self.error_description_label.set_line_wrap(True)
        self.info_box.pack_start(self.error_description_label, True, True, 0)

        self.connection_info_box = Gtk.HBox()
        icon = Icon(icon_name='data-upload',
                    pixel_size=style.SMALL_ICON_SIZE)
        self.connection_info_box.pack_start(icon, True, True, 0)
        icon.show()

        self._data_label_up = Gtk.Label()
        self._data_label_up.props.xalign = 0.0
        label_alignment = self._add_widget_with_padding(self._data_label_up)
        self.connection_info_box.pack_start(label_alignment, True, True, 0)
        self._data_label_up.show()
        label_alignment.show()

        icon = Icon(icon_name='data-download',
                    pixel_size=style.SMALL_ICON_SIZE)
        self.connection_info_box.pack_start(icon, True, True, 0)
        icon.show()
        self._data_label_down = Gtk.Label()
        self._data_label_down.props.xalign = 0.0
        label_alignment = self._add_widget_with_padding(self._data_label_down)
        self.connection_info_box.pack_start(label_alignment, True, True, 0)
        self._data_label_down.show()
        label_alignment.show()

        self.info_box.pack_start(self.connection_info_box, True, True, 0)

        self.info_box.show()
        self.set_content(self.info_box)

        self.update_state(_GSM_STATE_NOT_READY)

    def _add_widget_with_padding(self, child, xalign=0, yalign=0.5):
        alignment = Gtk.Alignment.new(xalign=xalign, yalign=yalign,
                                      xscale=1, yscale=0.33)
        alignment.set_padding(style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING,
                              style.DEFAULT_SPACING)
        alignment.add(child)
        return alignment

    def update_state(self, state, reason=0):
        self._current_state = state
        self._update_label_and_text(reason)

    def _update_label_and_text(self, reason=0):
        if self._current_state == _GSM_STATE_NOT_READY:
            self._toggle_state_item.set_label('...')
            self.props.secondary_text = _('Please wait...')

        elif self._current_state == _GSM_STATE_DISCONNECTED:
            if not self._failed_connection:
                self._toggle_state_item.set_label(_('Connect'))
            self.props.secondary_text = _('Disconnected')
            icon = Icon(icon_name='dialog-ok',
                        pixel_size=style.SMALL_ICON_SIZE)
            self._toggle_state_item.set_image(icon)

        elif self._current_state == _GSM_STATE_CONNECTING:
            self._toggle_state_item.set_label(_('Cancel'))
            self.props.secondary_text = _('Connecting...')
            icon = Icon(icon_name='dialog-cancel',
                        pixel_size=style.SMALL_ICON_SIZE)
            self._toggle_state_item.set_image(icon)

        elif self._current_state == _GSM_STATE_CONNECTED:
            self._failed_connection = False
            self._toggle_state_item.set_label(_('Disconnect'))
            self.update_connection_time()
            icon = Icon(icon_name='media-eject',
                        pixel_size=style.SMALL_ICON_SIZE)
            self._toggle_state_item.set_image(icon)

        elif self._current_state == _GSM_STATE_FAILED:
            message_error = self._get_error_by_nm_reason(reason)
            self.add_alert(message_error[0], message_error[1])
        else:
            raise ValueError('Invalid GSM state while updating label and '
                             'text, %s' % str(self._current_state))

    def __toggle_state_cb(self, menuitem):
        if self._current_state == _GSM_STATE_NOT_READY:
            pass
        elif self._current_state == _GSM_STATE_DISCONNECTED:
            self.error_title_label.hide()
            self.error_description_label.hide()
            self.emit('gsm-connect')
        elif self._current_state == _GSM_STATE_CONNECTING:
            self.emit('gsm-disconnect')
        elif self._current_state == _GSM_STATE_CONNECTED:
            self.emit('gsm-disconnect')
        else:
            raise ValueError('Invalid GSM state while emitting signal, %s' %
                             str(self._current_state))

    def add_alert(self, error, suggestion):
        self._failed_connection = True
        action = _('Try connection again')
        self._toggle_state_item.set_label(action)

        title = _('Error: %s') % error
        self.error_title_label.set_markup('<b>%s</b>' % title)
        self.error_title_label.show()

        message = _('Suggestion: %s') % suggestion
        self.error_description_label.set_text(message)
        self.error_description_label.show()

    def update_connection_time(self, connection_time=None):
        if connection_time is not None:
            formatted_time = connection_time.strftime('%H:%M:%S')
        else:
            formatted_time = '00:00:00'

        self.props.secondary_text = _('Connected for %s') % (formatted_time, )

    def update_stats(self, in_bytes, out_bytes):
        self._data_label_up.set_text(_('%d KiB') % (out_bytes / 1024))
        self._data_label_down.set_text(_('%d KiB') % (in_bytes / 1024))

    def _get_error_by_nm_reason(self, reason):
        if reason in [network.NM_DEVICE_STATE_REASON_NO_SECRETS,
                      network.NM_DEVICE_STATE_REASON_GSM_PIN_CHECK_FAILED]:
            message = _('Check your PIN/PUK configuration.')
        elif reason in [network.NM_DEVICE_STATE_REASON_PPP_DISCONNECT,
                        network.NM_DEVICE_STATE_REASON_PPP_FAILED]:
            message = _('Check your Access Point Name '
                        '(APN) configuration')
        elif reason in [network.NM_DEVICE_STATE_REASON_MODEM_NO_CARRIER,
                        network.NM_DEVICE_STATE_REASON_MODEM_DIAL_TIMEOUT]:
            message = _('Check the Number configuration.')
        elif reason == network.NM_DEVICE_STATE_REASON_CONFIG_FAILED:
            message = _('Check your configuration.')
        else:
            message = ''
        message_tuple = (network.get_error_by_reason(reason), message)
        return message_tuple


class WirelessDeviceView(ToolButton):

    FRAME_POSITION_RELATIVE = 302

    def __init__(self, device):
        ToolButton.__init__(self)

        self._bus = dbus.SystemBus()
        self._device = device
        self._device_props = None
        self._flags = 0
        self._ssid = ''
        self._display_name = ''
        self._mode = network.NM_802_11_MODE_UNKNOWN
        self._strength = 0
        self._frequency = 0
        self._device_state = None
        self._color = None
        self._active_ap_op = None

        self._icon = PulsingIcon()
        self._icon.props.icon_name = get_icon_state('network-wireless', 0)
        self._inactive_color = xocolor.XoColor(
            '%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                       style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulse_color = self._inactive_color
        self._icon.props.base_color = self._inactive_color

        self.set_icon_widget(self._icon)
        self._icon.show()

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.props.hide_tooltip_on_click = False
        self.palette_invoker.props.toggle_palette = True

        self._palette = WirelessPalette(self._display_name)
        self._palette.connect('deactivate-connection',
                              self.__deactivate_connection_cb)
        self.set_palette(self._palette)
        self._palette.set_group_id('frame')

        self._device_props = dbus.Interface(self._device,
                                            dbus.PROPERTIES_IFACE)
        self._device_props.GetAll(
            network.NM_DEVICE_IFACE, byte_arrays=True,
            reply_handler=self.__get_device_props_reply_cb,
            error_handler=self.__get_device_props_error_cb)

        self._device_props.Get(
            network.NM_WIRELESS_IFACE, 'ActiveAccessPoint',
            reply_handler=self.__get_active_ap_reply_cb,
            error_handler=self.__get_active_ap_error_cb)

        self._bus.add_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

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
                    dbus_interface=network.NM_ACCESSPOINT_IFACE)
            if active_ap_op == '/':
                self._active_ap_op = None
                return
            self._active_ap_op = active_ap_op
            active_ap = self._bus.get_object(network.NM_SERVICE, active_ap_op)
            props = dbus.Interface(active_ap, dbus.PROPERTIES_IFACE)

            props.GetAll(network.NM_ACCESSPOINT_IFACE, byte_arrays=True,
                         reply_handler=self.__get_all_ap_props_reply_cb,
                         error_handler=self.__get_all_ap_props_error_cb)

            self._bus.add_signal_receiver(
                self.__ap_properties_changed_cb,
                signal_name='PropertiesChanged',
                path=self._active_ap_op,
                dbus_interface=network.NM_ACCESSPOINT_IFACE,
                byte_arrays=True)

    def __get_active_ap_error_cb(self, err):
        logging.error('Error getting the active access point: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._device_state = new_state
        self._update_color()
        self._update_state()
        self._device_props.Get(network.NM_WIRELESS_IFACE, 'ActiveAccessPoint',
                               reply_handler=self.__get_active_ap_reply_cb,
                               error_handler=self.__get_active_ap_error_cb)

    def __ap_properties_changed_cb(self, properties):
        self._update_properties(properties)

    def _update_properties(self, properties):
        if 'Mode' in properties:
            self._mode = properties['Mode']
            self._color = None
        if 'Ssid' in properties:
            self._ssid = properties['Ssid']
            self._display_name = network.ssid_to_display_name(self._ssid)
            self._color = None
        if 'Strength' in properties:
            self._strength = properties['Strength']
        if 'Flags' in properties:
            self._flags = properties['Flags']
        if 'Frequency' in properties:
            self._frequency = properties['Frequency']

        if self._color is None:
            if self._mode == network.NM_802_11_MODE_ADHOC and \
                    network.is_sugar_adhoc_network(self._ssid):
                self._color = profile.get_color()
            else:
                sha_hash = hashlib.sha1()
                data = self._ssid + hex(self._flags)
                sha_hash.update(data)
                digest = hash(sha_hash.digest())
                index = digest % len(xocolor.colors)

                self._color = xocolor.XoColor('%s,%s' %
                                              (xocolor.colors[index][0],
                                               xocolor.colors[index][1]))
        self._update()

    def __get_all_ap_props_reply_cb(self, properties):
        self._update_properties(properties)

    def __get_all_ap_props_error_cb(self, err):
        logging.error('Error getting the access point properties: %s', err)

    def _update(self):
        if self._flags == network.NM_802_11_AP_FLAGS_PRIVACY:
            self._icon.props.badge_name = 'emblem-locked'
        else:
            self._icon.props.badge_name = None

        self._palette.props.primary_text = self._display_name

        self._update_state()
        self._update_color()

    def _update_state(self):
        if self._active_ap_op is not None:
            state = self._device_state
        else:
            state = network.NM_DEVICE_STATE_UNKNOWN

        if self._mode != network.NM_802_11_MODE_ADHOC or \
                network.is_sugar_adhoc_network(self._ssid) is False:
            if state == network.NM_DEVICE_STATE_ACTIVATED:
                icon_name = '%s-connected' % 'network-wireless'
            else:
                icon_name = 'network-wireless'

            icon_name = get_icon_state(icon_name, self._strength)
            if icon_name:
                self._icon.props.icon_name = icon_name
        else:
            channel = network.frequency_to_channel(self._frequency)
            if state == network.NM_DEVICE_STATE_ACTIVATED:
                self._icon.props.icon_name = 'network-adhoc-%s-connected' \
                    % channel
            else:
                self._icon.props.icon_name = 'network-adhoc-%s' % channel
            self._icon.props.base_color = profile.get_color()

        if state == network.NM_DEVICE_STATE_PREPARE or \
           state == network.NM_DEVICE_STATE_CONFIG or \
           state == network.NM_DEVICE_STATE_NEED_AUTH or \
           state == network.NM_DEVICE_STATE_IP_CONFIG or \
           state == network.NM_DEVICE_STATE_IP_CHECK or \
           state == network.NM_DEVICE_STATE_SECONDARIES:
            self._palette.set_connecting()
            self._icon.props.pulsing = True
        elif state == network.NM_DEVICE_STATE_ACTIVATED:

            def _ip_cb(ip):
                self._palette.set_connected_with_frequency(self._frequency,
                                                           ip)
                self._icon.props.pulsing = False

            _get_ip(self._bus, self._device_props, _ip_cb)
        else:
            self._icon.props.badge_name = None
            self._icon.props.pulsing = False
            self._icon.props.pulse_color = self._inactive_color
            self._icon.props.base_color = self._inactive_color
            self._palette.set_disconnected()

    def _update_color(self):
        self._icon.props.base_color = self._color

    def __deactivate_connection_cb(self, palette, data=None):
        network.disconnect_access_points([self._active_ap_op])

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
        self._inactive_color = xocolor.XoColor(
            '%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                       style.COLOR_TRANSPARENT.get_svg()))
        self._icon.props.pulse_color = profile.get_color()
        self._icon.props.base_color = self._inactive_color

        self.set_icon_widget(self._icon)
        self._icon.show()

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.props.hide_tooltip_on_click = False
        self.palette_invoker.props.toggle_palette = True

        self._palette = WirelessPalette(_('Mesh Network'))
        self._palette.connect('deactivate-connection',
                              self.__deactivate_connection)
        self.set_palette(self._palette)
        self._palette.set_group_id('frame')

        self.update_state(state)

        self._device_props = dbus.Interface(self._device,
                                            dbus.PROPERTIES_IFACE)
        self._device_props.Get(
            network.NM_OLPC_MESH_IFACE, 'ActiveChannel',
            reply_handler=self.__get_active_channel_reply_cb,
            error_handler=self.__get_active_channel_error_cb)

        self._bus.add_signal_receiver(
            self.__wireless_properties_changed_cb,
            signal_name='PropertiesChanged',
            path=device.object_path,
            dbus_interface=network.NM_OLPC_MESH_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(
            self.__wireless_properties_changed_cb,
            signal_name='PropertiesChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_OLPC_MESH_IFACE)

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
        channel = str(self._channel)
        self._palette.props.primary_text = _('Mesh Network %s') % (channel, )

    def _update(self):
        state = self._device_state

        if (state >= network.NM_DEVICE_STATE_PREPARE) and \
           (state <= network.NM_DEVICE_STATE_IP_CONFIG):
            self._icon.props.base_color = self._inactive_color
            self._icon.props.pulse_color = profile.get_color()
            self._palette.set_connecting()
            self._icon.props.pulsing = True
        elif state == network.NM_DEVICE_STATE_ACTIVATED:

            def _ip_cb(ip):
                self._icon.props.pulsing = False
                self._palette.set_connected_with_channel(self._channel, ip)
                self._icon.props.base_color = profile.get_color()
                self._icon.props.pulsing = False

            _get_ip(self._bus, self._device_props, _ip_cb)
        self._update_text()

    def update_state(self, state):
        self._device_state = state
        self._update()

    def __deactivate_connection(self, palette, data=None):
        obj = self._bus.get_object(network.NM_SERVICE, network.NM_PATH)
        netmgr = dbus.Interface(obj, network.NM_IFACE)
        netmgr_props = dbus.Interface(netmgr, dbus.PROPERTIES_IFACE)
        active_connections_o = netmgr_props.Get(network.NM_IFACE,
                                                'ActiveConnections')

        for conn_o in active_connections_o:
            # The connection path for a mesh connection is the device itself.
            obj = self._bus.get_object(network.NM_IFACE, conn_o)
            props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            ap_op = props.Get(network.NM_ACTIVE_CONN_IFACE, 'SpecificObject')

            try:
                obj = self._bus.get_object(network.NM_IFACE, ap_op)
                props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
                device_type = props.Get(network.NM_DEVICE_IFACE, 'DeviceType')
                if device_type == network.NM_DEVICE_TYPE_OLPC_MESH:
                    netmgr.DeactivateConnection(conn_o)
                    break
            except dbus.exceptions.DBusException:
                pass


class WiredDeviceView(TrayIcon):

    _ICON_NAME = 'network-wired'
    FRAME_POSITION_RELATIVE = 301

    def __init__(self, speed, address):
        color = profile.get_color()

        TrayIcon.__init__(self, icon_name=self._ICON_NAME, xo_color=color)

        self.set_palette_invoker(FrameWidgetInvoker(self))
        self._palette = WiredPalette()
        self.set_palette(self._palette)
        self._palette.set_group_id('frame')
        self._palette.set_connected(speed, address)
        self.palette_invoker.props.toggle_palette = True


class GsmDeviceView(TrayIcon):

    _ICON_NAME = 'network-gsm'
    FRAME_POSITION_RELATIVE = 303

    def __init__(self, device):
        self._connection_time_handler = None

        self._connection_timestamp = 0

        color = profile.get_color()

        TrayIcon.__init__(self, icon_name=self._ICON_NAME, xo_color=color)

        self._bus = dbus.SystemBus()
        self._device = device
        self._palette = None
        self.set_palette_invoker(FrameWidgetInvoker(self))
        self.palette_invoker.props.toggle_palette = True

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=network.NM_DEVICE_IFACE)
        self._bus.add_signal_receiver(self.__ppp_stats_changed_cb,
                                      signal_name='PppStats',
                                      path=self._device.object_path,
                                      dbus_interface=network.NM_MODEM_IFACE)

    def create_palette(self):
        palette = GsmPalette()

        palette.set_group_id('frame')
        palette.connect('gsm-connect', self.__gsm_connect_cb)
        palette.connect('gsm-disconnect', self.__gsm_disconnect_cb)

        self._palette = palette

        props = dbus.Interface(self._device, dbus.PROPERTIES_IFACE)
        props.GetAll(network.NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__current_state_check_cb,
                     error_handler=self.__current_state_check_error_cb)

        return palette

    def __gsm_connect_cb(self, palette, data=None):
        connection = network.find_gsm_connection()
        if connection is not None:
            connection.activate(self._device.object_path,
                                reply_handler=self.__connect_cb,
                                error_handler=self.__connect_error_cb)
        else:
            self._palette.add_alert(_('No GSM connection available.'),
                                    _('Create a connection in My Settings.'))

    def __connect_cb(self, active_connection):
        logging.debug('Connected successfully to gsm device, %s',
                      active_connection)

    def __connect_error_cb(self, error):
        raise RuntimeError('Error when connecting to gsm device, %s' % error)

    def __gsm_disconnect_cb(self, palette, data=None):
        obj = self._bus.get_object(network.NM_SERVICE, network.NM_PATH)
        netmgr = dbus.Interface(obj, network.NM_IFACE)
        netmgr_props = dbus.Interface(netmgr, dbus.PROPERTIES_IFACE)
        active_connections_o = netmgr_props.Get(
            network.NM_IFACE, 'ActiveConnections')

        for conn_o in active_connections_o:
            obj = self._bus.get_object(network.NM_IFACE, conn_o)
            props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            devices = props.Get(network.NM_ACTIVE_CONN_IFACE, 'Devices')
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
        logging.debug('State: %s to %s, reason %s', old_state,
                      new_state, reason)
        self._update_state(int(new_state), int(old_state), int(reason))

    def __current_state_check_cb(self, properties):
        self._update_state(int(properties['State']), 0, 0)

    def __current_state_check_error_cb(self, error):
        raise RuntimeError('Error when checking gsm device state, %s' % error)

    def _update_state(self, state, old_state, reason):
        gsm_state = None

        if state is network.NM_DEVICE_STATE_ACTIVATED:
            gsm_state = _GSM_STATE_CONNECTED
            connection = network.find_gsm_connection()
            if connection is not None:
                self._connection_timestamp = time.time() - \
                    connection.get_settings('connection')['timestamp']
                self._connection_time_handler = GObject.timeout_add_seconds(
                    1, self.__connection_timecount_cb)
                self._palette.update_connection_time()
                self._palette.update_stats(0, 0)
                if self._palette is not None:
                    self._palette.connection_info_box.show()

        elif state is network.NM_DEVICE_STATE_DISCONNECTED:
            gsm_state = _GSM_STATE_DISCONNECTED
            self._connection_timestamp = 0
            if self._connection_time_handler is not None:
                GObject.source_remove(self._connection_time_handler)
            if self._palette is not None:
                self._palette.connection_info_box.hide()

        elif state in [network.NM_DEVICE_STATE_UNMANAGED,
                       network.NM_DEVICE_STATE_UNAVAILABLE,
                       network.NM_DEVICE_STATE_UNKNOWN]:
            gsm_state = _GSM_STATE_NOT_READY

        elif (state >= network.NM_DEVICE_STATE_PREPARE) and \
             (state < network.NM_DEVICE_STATE_ACTIVATED):
            gsm_state = _GSM_STATE_CONNECTING

        elif state == network.NM_DEVICE_STATE_FAILED:
            gsm_state = _GSM_STATE_FAILED

        if self._palette is not None:
            self._palette.update_state(gsm_state, reason)

    def disconnect(self):
        self._bus.remove_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

    def __ppp_stats_changed_cb(self, in_bytes, out_bytes):
        self._palette.update_stats(in_bytes, out_bytes)

    def __connection_timecount_cb(self):
        self._connection_timestamp = self._connection_timestamp + 1
        connection_time = \
            datetime.datetime.fromtimestamp(self._connection_timestamp)
        self._palette.update_connection_time(connection_time)
        return True


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
        props.GetAll(network.NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__get_device_props_reply_cb,
                     error_handler=self.__get_device_props_error_cb)

        self._bus.add_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

    def _remove_device_view(self):
        self._device_view.disconnect()
        self._tray.remove_device(self._device_view)
        self._device_view = None

    def disconnect(self):
        if self._device_view is not None:
            self._remove_device_view()

        self._bus.remove_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

    def __get_device_props_reply_cb(self, properties):
        if 'State' in properties:
            self._update_state(properties['State'])

    def __get_device_props_error_cb(self, err):
        logging.error('Error getting the device properties: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._update_state(new_state)

    def _update_state(self, state):
        if (state >= network.NM_DEVICE_STATE_PREPARE) and \
           (state <= network.NM_DEVICE_STATE_ACTIVATED):
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
        props.GetAll(network.NM_DEVICE_IFACE, byte_arrays=True,
                     reply_handler=self.__get_device_props_reply_cb,
                     error_handler=self.__get_device_props_error_cb)

        self._bus.add_signal_receiver(self.__state_changed_cb,
                                      signal_name='StateChanged',
                                      path=self._device.object_path,
                                      dbus_interface=network.NM_DEVICE_IFACE)

    def disconnect(self):
        self._bus.remove_signal_receiver(
            self.__state_changed_cb,
            signal_name='StateChanged',
            path=self._device.object_path,
            dbus_interface=network.NM_DEVICE_IFACE)

    def __get_device_props_reply_cb(self, properties):
        if 'State' in properties:
            self._update_state(properties['State'])

    def __get_device_props_error_cb(self, err):
        logging.error('Error getting the device properties: %s', err)

    def __state_changed_cb(self, new_state, old_state, reason):
        self._update_state(new_state)

    def _update_state(self, state):
        if state == network.NM_DEVICE_STATE_ACTIVATED:
            props = dbus.Interface(self._device, dbus.PROPERTIES_IFACE)
            speed = props.Get(network.NM_WIRED_IFACE, 'Speed')

            def _ip_cb(ip):
                self._device_view = WiredDeviceView(speed, ip)
                self._tray.add_device(self._device_view)

            _get_ip(self._bus, props, _ip_cb)
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
            obj = self._bus.get_object(network.NM_SERVICE, network.NM_PATH)
            self._netmgr = dbus.Interface(obj, network.NM_IFACE)
        except dbus.DBusException:
            logging.error('%s service not available', network.NM_SERVICE)
            return

        self._netmgr.GetDevices(reply_handler=self.__get_devices_reply_cb,
                                error_handler=self.__get_devices_error_cb)

        self._bus.add_signal_receiver(self.__device_added_cb,
                                      signal_name='DeviceAdded',
                                      dbus_interface=network.NM_IFACE)
        self._bus.add_signal_receiver(self.__device_removed_cb,
                                      signal_name='DeviceRemoved',
                                      dbus_interface=network.NM_IFACE)

    def __get_devices_reply_cb(self, devices):
        for device_op in devices:
            self._check_device(device_op)

    def __get_devices_error_cb(self, err):
        logging.error('Failed to get devices: %s', err)

    def _check_device(self, device_op):
        if device_op in self._devices:
            return

        nm_device = self._bus.get_object(network.NM_SERVICE, device_op)
        props = dbus.Interface(nm_device, dbus.PROPERTIES_IFACE)

        device_type = props.Get(network.NM_DEVICE_IFACE, 'DeviceType')
        if device_type == network.NM_DEVICE_TYPE_ETHERNET:
            device = WiredDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device
        elif device_type == network.NM_DEVICE_TYPE_WIFI:
            device = WirelessDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device
        elif device_type == network.NM_DEVICE_TYPE_OLPC_MESH:
            device = MeshDeviceObserver(nm_device, self._tray)
            self._devices[device_op] = device
        elif device_type == network.NM_DEVICE_TYPE_MODEM:
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
    NetworkManagerObserver(tray)
