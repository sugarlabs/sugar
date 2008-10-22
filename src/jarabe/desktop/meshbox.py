# Copyright (C) 2006-2007 Red Hat, Inc.
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

import dbus
import hippo
import gobject
import gtk

from sugar.graphics.icon import CanvasIcon, Icon
from sugar.graphics.xocolor import XoColor
from sugar.graphics import xocolor
from sugar.graphics import style
from sugar.graphics.icon import get_icon_state
from sugar.graphics import palette
from sugar.graphics import iconentry
from sugar.graphics.menuitem import MenuItem
from sugar.activity.activityhandle import ActivityHandle
from sugar.activity import activityfactory
from sugar.util import unique_id

from jarabe.model import neighborhood
from jarabe.view.buddyicon import BuddyIcon
from jarabe.view.pulsingicon import CanvasPulsingIcon
from jarabe.desktop.snowflakelayout import SnowflakeLayout
from jarabe.desktop.spreadlayout import SpreadLayout
from jarabe.model import bundleregistry
from jarabe.model import network

_NM_SERVICE = 'org.freedesktop.NetworkManager'
_NM_IFACE = 'org.freedesktop.NetworkManager'
_NM_PATH = '/org/freedesktop/NetworkManager'
_NM_DEVICE_IFACE = 'org.freedesktop.NetworkManager.Device'
_NM_WIRELESS_IFACE = 'org.freedesktop.NetworkManager.Device.Wireless'
_NM_ACCESSPOINT_IFACE = 'org.freedesktop.NetworkManager.AccessPoint'

_ICON_NAME = 'network-wireless'

class AccessPointView(CanvasPulsingIcon):
    def __init__(self, device, model):
        CanvasPulsingIcon.__init__(self, size=style.STANDARD_ICON_SIZE,
                                   cache=True)
        self._bus = dbus.SystemBus()
        self._device = device
        self._model = model
        self._disconnect_item = None
        self._connect_item = None
        self._greyed_out = False
        self._name = ''
        self._strength = 0
        self._flags = 0
        self._device_state = None
        self._active = True

        self.connect('activated', self._activate_cb)

        pulse_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                         style.COLOR_TRANSPARENT.get_svg()))
        self.props.pulse_color = pulse_color

        self._palette = self._create_palette()
        self.set_palette(self._palette)

        model_props = dbus.Interface(model, 'org.freedesktop.DBus.Properties')
        model_props.GetAll(_NM_ACCESSPOINT_IFACE, byte_arrays=True,
                           reply_handler=self.__get_all_props_reply_cb,
                           error_handler=self.__get_all_props_error_cb)

        self._bus.add_signal_receiver(self.__ap_properties_changed_cb,
                                      signal_name='PropertiesChanged',
                                      path=model.object_path,
                                      dbus_interface=_NM_ACCESSPOINT_IFACE)

        self._device.Get(_NM_DEVICE_IFACE, 'State',
                         reply_handler=self.__get_device_state_reply_cb,
                         error_handler=self.__get_device_state_error_cb)
        self._device.Get(_NM_WIRELESS_IFACE, 'ActiveAccessPoint',
                         reply_handler=self.__get_active_ap_reply_cb,
                         error_handler=self.__get_active_ap_error_cb)

        self._bus.add_signal_receiver(self.__device_state_changed_cb,
                                      signal_name='StateChanged',
                                      path=device.object_path,
                                      dbus_interface=_NM_DEVICE_IFACE)
        self._bus.add_signal_receiver(self.__wireless_properties_changed_cb,
                                      signal_name='PropertiesChanged',
                                      path=device.object_path,
                                      dbus_interface=_NM_WIRELESS_IFACE)

    def _create_palette(self):
        icon_name = get_icon_state(_ICON_NAME, self._strength)
        palette_icon = Icon(icon_name=icon_name,
                            icon_size=style.STANDARD_ICON_SIZE,
                            badge_name=self.props.badge_name)
        palette_icon.props.xo_color = XoColor('%s,%s' % self._compute_color())
                                              
        p = palette.Palette(primary_text=self._name,
                            icon=palette_icon)

        self._connect_item = MenuItem(_('Connect'), 'dialog-ok')
        self._connect_item.connect('activate', self._activate_cb)
        p.menu.append(self._connect_item)

        self._disconnect_item = MenuItem(_('Disconnect'), 'media-eject')
        self._disconnect_item.connect('activate',
                                        self._disconnect_activate_cb)
        p.menu.append(self._disconnect_item)

        return p

    def __device_state_changed_cb(self, old_state, new_state, reason):
        self._device_state = new_state
        self._update()

    def __ap_properties_changed_cb(self, properties):
        self._update_properties(properties)

    def __wireless_properties_changed_cb(self, properties):
        if 'ActiveAccessPoint' in properties:
            ap = properties['ActiveAccessPoint']
            self._active = (ap == self._model.object_path)
            self._update_state()

    def _update_properties(self, props):
        if 'Ssid' in props:
            self._name = props['Ssid']
        if 'Strength' in props:
            self._strength = props['Strength']
        if 'Flags' in props:
            self._flags = props['Flags']

        self._update()

    def _compute_color(self):
        sh = sha.new()
        data = self._name + hex(self._flags)
        sh.update(data)
        h = hash(sh.digest())
        idx = h % len(xocolor.colors)

        # stroke, fill
        return (xocolor.colors[idx][0], xocolor.colors[idx][1])

    def __get_active_ap_reply_cb(self, ap):
        self._active = (ap == self._model.object_path)
        self._update_state()

    def __get_active_ap_error_cb(self, err):
        logging.debug('Error getting the active access point: %s', err)

    def __get_device_state_reply_cb(self, state):
        self._device_state = state
        self._update()

    def __get_device_state_error_cb(self, err):
        logging.debug('Error getting the access point properties: %s', err)

    def __get_all_props_reply_cb(self, properties):
        self._update_properties(properties)

    def __get_all_props_error_cb(self, err):
        logging.debug('Error getting the access point properties: %s', err)

    def _update(self):
        if self._flags == network.AP_FLAGS_802_11_PRIVACY:
            self.props.badge_name = "emblem-locked"
        else:
            self.props.badge_name = None

        self._palette.props.primary_text = self._name

        self._update_state()

    def _update_state(self):
        if self._active:
            state = self._device_state
        else:
            state = network.DEVICE_STATE_UNKNOWN

        if state == network.DEVICE_STATE_ACTIVATED:
            icon_name = '%s-connected' % _ICON_NAME
        else:
            icon_name = _ICON_NAME

        icon_name = get_icon_state(icon_name, self._strength)
        if icon_name:
            self.props.icon_name = icon_name
            icon = self._palette.props.icon
            icon.props.icon_name = icon_name

        if state == network.DEVICE_STATE_PREPARE or \
           state == network.DEVICE_STATE_CONFIG or \
           state == network.DEVICE_STATE_NEED_AUTH or \
           state == network.DEVICE_STATE_IP_CONFIG:
            if self._disconnect_item:
                self._disconnect_item.show()
            self._connect_item.hide()
            self._palette.props.secondary_text = _('Connecting...')
            self.props.pulsing = True
        elif state == network.DEVICE_STATE_ACTIVATED:
            if self._disconnect_item:
                self._disconnect_item.show()
            self._connect_item.hide()
            self._palette.props.secondary_text = _('Connected')
            self.props.pulsing = False
        else:
            if self._disconnect_item:
                self._disconnect_item.hide()
            self._connect_item.show()
            self._palette.props.secondary_text = None
            self.props.pulsing = False

        if self._greyed_out:
            self.props.pulsing = False
            self.props.base_color = XoColor('#D5D5D5,#D5D5D5')
        else:
            self.props.base_color = XoColor('%s,%s' % self._compute_color())

    def _disconnect_activate_cb(self, item):
        pass

    def _activate_cb(self, icon):
        info = { 'connection': { 'id' : 'Auto ' + self._name,
                                 'uuid' : unique_id(),
                                 'type' : '802-11-wireless' } ,
                 '802-11-wireless' : { 'ssid': self._name }
               }
        conn = network.add_connection(info)

        obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
        netmgr = dbus.Interface(obj, _NM_IFACE)
        netmgr.ActivateConnection(network.SETTINGS_SERVICE, conn.path,
                                  self._device.object_path,
                                  self._model.object_path,
                                  reply_handler=self.__activate_reply_cb,
                                  error_handler=self.__activate_error_cb)

    def __activate_reply_cb(self, connection):
        logging.debug('Connection activated: %s', connection)

    def __activate_error_cb(self, err):
        logging.debug('Failed to activate connection: %s', err)

    def set_filter(self, query):
        self._greyed_out = self._name.lower().find(query) == -1
        self._update_state()

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__ap_properties_changed_cb,
                                         signal_name='PropertiesChanged',
                                         path=self._model.object_path,
                                         dbus_interface=_NM_ACCESSPOINT_IFACE)

        self._bus.remove_signal_receiver(self.__device_state_changed_cb,
                                         signal_name='StateChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_DEVICE_IFACE)
        self._bus.remove_signal_receiver(self.__wireless_properties_changed_cb,
                                         signal_name='PropertiesChanged',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_WIRELESS_IFACE)

class ActivityView(hippo.CanvasBox):
    def __init__(self, model):
        hippo.CanvasBox.__init__(self)

        self._model = model
        self._icons = {}
        self._palette = None

        self._layout = SnowflakeLayout()
        self.set_layout(self._layout)

        self._icon = self._create_icon()
        self._layout.add(self._icon, center=True)

        self._update_palette()

        activity = self._model.activity
        activity.connect('notify::name', self._name_changed_cb)
        activity.connect('notify::color', self._color_changed_cb)
        activity.connect('notify::private', self._private_changed_cb)
        activity.connect('joined', self._joined_changed_cb)
        #FIXME: 'joined' signal not working, see #5032

    def _create_icon(self):
        icon = CanvasIcon(file_name=self._model.get_icon_name(),
                    xo_color=self._model.get_color(), cache=True,
                    size=style.STANDARD_ICON_SIZE)
        icon.connect('activated', self._clicked_cb)
        return icon

    def _create_palette(self):
        p_icon = Icon(file=self._model.get_icon_name(),
                      xo_color=self._model.get_color())
        p_icon.props.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
        p = palette.Palette(None, primary_text=self._model.activity.props.name,
                            icon=p_icon)

        private = self._model.activity.props.private
        joined = self._model.activity.props.joined

        if joined:
            item = MenuItem(_('Resume'), 'activity-start')
            item.connect('activate', self._clicked_cb)
            item.show()
            p.menu.append(item)
        elif not private:
            item = MenuItem(_('Join'), 'activity-start')
            item.connect('activate', self._clicked_cb)
            item.show()
            p.menu.append(item)

        return p

    def _update_palette(self):
        self._palette = self._create_palette()
        self._icon.set_palette(self._palette)

    def has_buddy_icon(self, key):
        return self._icons.has_key(key)

    def add_buddy_icon(self, key, icon):
        self._icons[key] = icon
        self._layout.add(icon)

    def remove_buddy_icon(self, key):
        icon = self._icons[key]
        del self._icons[key]
        icon.destroy()

    def _clicked_cb(self, item):
        bundle_id = self._model.get_bundle_id()

        handle = ActivityHandle(self._model.get_id())

        bundle = bundleregistry.get_registry().get_bundle(bundle_id)
        activityfactory.create(bundle, handle)

    def set_filter(self, query):
        text_to_check = self._model.activity.props.name.lower() + \
                self._model.activity.props.type.lower()
        if text_to_check.find(query) == -1:
            self._icon.props.stroke_color = '#D5D5D5'
            self._icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()
        else:
            self._icon.props.xo_color = self._model.get_color()

        for icon in self._icons.itervalues():
            if hasattr(icon, 'set_filter'):
                icon.set_filter(query)

    def _name_changed_cb(self, activity, pspec):
        self._update_palette()

    def _color_changed_cb(self, activity, pspec):
        self._layout.remove(self._icon)
        self._icon = self._create_icon()
        self._layout.add(self._icon, center=True)
        self._icon.set_palette(self._palette)

    def _private_changed_cb(self, activity, pspec):
        self._update_palette()

    def _joined_changed_cb(self, widget, event):
        logging.debug('ActivityView._joined_changed_cb')

_AUTOSEARCH_TIMEOUT = 1000

class MeshToolbar(gtk.Toolbar):
    __gtype_name__ = 'MeshToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST,
                          gobject.TYPE_NONE,
                          ([str]))
    }

    def __init__(self):
        gtk.Toolbar.__init__(self)

        self._query = None
        self._autosearch_timer = None

        self._add_separator()

        tool_item = gtk.ToolItem()
        self.insert(tool_item, -1)
        tool_item.show()

        self.search_entry = iconentry.IconEntry()
        self.search_entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'system-search')
        self.search_entry.add_clear_button()
        self.search_entry.set_width_chars(25)
        self.search_entry.connect('activate', self._entry_activated_cb)
        self.search_entry.connect('changed', self._entry_changed_cb)
        tool_item.add(self.search_entry)
        self.search_entry.show()

        self._add_separator(expand=True)

    def _add_separator(self, expand=False):
        separator = gtk.SeparatorToolItem()
        separator.props.draw = False
        if expand:
            separator.set_expand(True)
        else:
            separator.set_size_request(style.GRID_CELL_SIZE,
                                       style.GRID_CELL_SIZE)
        self.insert(separator, -1)
        separator.show()

    def _entry_activated_cb(self, entry):
        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        new_query = entry.props.text
        if self._query != new_query:
            self._query = new_query
            self.emit('query-changed', self._query)

    def _entry_changed_cb(self, entry):
        if not entry.props.text:
            entry.activate()
            return

        if self._autosearch_timer:
            gobject.source_remove(self._autosearch_timer)
        self._autosearch_timer = gobject.timeout_add(_AUTOSEARCH_TIMEOUT,
                                                     self._autosearch_timer_cb)

    def _autosearch_timer_cb(self):
        logging.debug('_autosearch_timer_cb')
        self._autosearch_timer = None
        self.search_entry.activate()
        return False

class DeviceObserver(object):
    def __init__(self, box, device):
        self._box = box
        self._bus = dbus.SystemBus()
        self._device = device

        self._device.GetAccessPoints(
                               reply_handler=self._get_access_points_reply_cb,
                               error_handler=self._get_access_points_error_cb)

        self._bus.add_signal_receiver(self.__access_point_added_cb,
                                      signal_name='AccessPointAdded',
                                      path=device.object_path,
                                      dbus_interface=_NM_WIRELESS_IFACE)
        self._bus.add_signal_receiver(self.__access_point_removed_cb,
                                      signal_name='AccessPointRemoved',
                                      path=device.object_path,
                                      dbus_interface=_NM_WIRELESS_IFACE)

    def _get_access_points_reply_cb(self, access_points_o):
        for ap_o in access_points_o:
            ap = self._bus.get_object(_NM_SERVICE, ap_o)
            self._box.add_access_point(self._device, ap)

    def _get_access_points_error_cb(self, err):
        logging.error('Failed to get access points: %s', err)

    def __access_point_added_cb(self, access_point_o):
        ap = self._bus.get_object(_NM_SERVICE, access_point_o)
        self._box.add_access_point(self._device, ap)

    def __access_point_removed_cb(self, access_point_o):
        self._box.remove_access_point(access_point_o)

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__access_point_added_cb,
                                         signal_name='AccessPointAdded',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_WIRELESS_IFACE)
        self._bus.remove_signal_receiver(self.__access_point_removed_cb,
                                         signal_name='AccessPointRemoved',
                                         path=self._device.object_path,
                                         dbus_interface=_NM_WIRELESS_IFACE)

class NetworkManagerObserver(object):
    def __init__(self, box):
        self._box = box
        self._bus = dbus.SystemBus()
        self._devices = {}

    def listen(self):
        try:
            obj = self._bus.get_object(_NM_SERVICE, _NM_PATH)
            netmgr = dbus.Interface(obj, _NM_IFACE)
        except dbus.DBusException:
            logging.debug('%s service not available', _NM_SERVICE)
            return

        netmgr.GetDevices(reply_handler=self._get_devices_reply_cb,
                          error_handler=self._get_devices_error_cb)

        self._bus.add_signal_receiver(self.__device_added_cb,
                                      signal_name='DeviceAdded',
                                      dbus_interface=_NM_DEVICE_IFACE)
        self._bus.add_signal_receiver(self.__device_removed_cb,
                                      signal_name='DeviceRemoved',
                                      dbus_interface=_NM_DEVICE_IFACE)

    def _get_devices_reply_cb(self, devices_o):
        for dev_o in devices_o:
            self._check_device(dev_o)

    def _get_devices_error_cb(self, err):
        logging.error('Failed to get devices: %s', err)

    def _check_device(self, device_o):
        device = self._bus.get_object(_NM_SERVICE, device_o)
        props = dbus.Interface(device, 'org.freedesktop.DBus.Properties')

        device_type = props.Get(_NM_DEVICE_IFACE, 'DeviceType')
        if device_type == network.DEVICE_TYPE_802_11_WIRELESS:
            self._devices[device_o] = DeviceObserver(self._box, device)

    def _get_device_path_error_cb(self, err):
        logging.error('Failed to get device type: %s', err)

    def __device_added_cb(self, device_o):
        self._check_device(device_o)

    def __device_removed_cb(self, device_o):
        if device_o in self._devices:
            observer = self._devices[device_o]
            observer.disconnect()
            del self._devices[device_o]

class MeshBox(gtk.VBox):
    __gtype_name__ = 'SugarMeshBox'

    def __init__(self):
        logging.debug("STARTUP: Loading the mesh view")

        gobject.GObject.__init__(self)

        self._model = neighborhood.get_model()
        self._buddies = {}
        self._activities = {}
        self._access_points = {}
        self._mesh = {}
        self._buddy_to_activity = {}
        self._suspended = True
        self._query = ''
        self._owner_icon = None
            
        self._toolbar = MeshToolbar()
        self._toolbar.connect('query-changed', self._toolbar_query_changed_cb)
        self.pack_start(self._toolbar, expand=False)
        self._toolbar.show()

        canvas = hippo.Canvas()
        self.add(canvas)
        canvas.show()

        self._layout_box = hippo.CanvasBox( \
                background_color=style.COLOR_WHITE.get_int())
        canvas.set_root(self._layout_box)

        self._layout = SpreadLayout()
        self._layout_box.set_layout(self._layout)

        for buddy_model in self._model.get_buddies():
            self._add_alone_buddy(buddy_model)

        self._model.connect('buddy-added', self._buddy_added_cb)
        self._model.connect('buddy-removed', self._buddy_removed_cb)
        self._model.connect('buddy-moved', self._buddy_moved_cb)

        for activity_model in self._model.get_activities():
            self._add_activity(activity_model)

        self._model.connect('activity-added', self._activity_added_cb)
        self._model.connect('activity-removed', self._activity_removed_cb)

        netmgr_observer = NetworkManagerObserver(self)
        netmgr_observer.listen()

    def do_size_allocate(self, allocation):
        width = allocation.width        
        height = allocation.height

        min_w_, icon_width = self._owner_icon.get_width_request()
        min_h_, icon_height = self._owner_icon.get_height_request(icon_width)
        x = (width - icon_width) / 2
        y = (height - icon_height) / 2 - style.GRID_CELL_SIZE
        self._layout.move(self._owner_icon, x, y)

        gtk.VBox.do_size_allocate(self, allocation)

    def _buddy_added_cb(self, model, buddy_model):
        self._add_alone_buddy(buddy_model)

    def _buddy_removed_cb(self, model, buddy_model):
        self._remove_buddy(buddy_model) 

    def _buddy_moved_cb(self, model, buddy_model, activity_model):
        # Owner doesn't move from the center
        if buddy_model.is_owner():
            return
        self._move_buddy(buddy_model, activity_model)

    def _activity_added_cb(self, model, activity_model):
        self._add_activity(activity_model)

    def _activity_removed_cb(self, model, activity_model):
        self._remove_activity(activity_model) 

    def _access_point_added_cb(self, model, ap_model):
        self._add_access_point(ap_model)

    def _access_point_removed_cb(self, model, ap_model):
        self._remove_access_point(ap_model) 

    def _add_alone_buddy(self, buddy_model):
        icon = BuddyIcon(buddy_model)
        if buddy_model.is_owner():
            self._owner_icon = icon
        self._layout.add(icon)

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._buddies[buddy_model.get_buddy().object_path()] = icon

    def _remove_alone_buddy(self, buddy_model):
        icon = self._buddies[buddy_model.get_buddy().object_path()]
        self._layout.remove(icon)
        del self._buddies[buddy_model.get_buddy().object_path()]
        icon.destroy()

    def _remove_buddy(self, buddy_model):
        object_path = buddy_model.get_buddy().object_path()
        if self._buddies.has_key(object_path):
            self._remove_alone_buddy(buddy_model)
        else:
            for activity in self._activities.values():
                if activity.has_buddy_icon(object_path):
                    activity.remove_buddy_icon(object_path)

    def _move_buddy(self, buddy_model, activity_model):
        self._remove_buddy(buddy_model)

        if activity_model == None:
            self._add_alone_buddy(buddy_model)
        elif activity_model.get_id() in self._activities:
            activity = self._activities[activity_model.get_id()]

            icon = BuddyIcon(buddy_model, style.STANDARD_ICON_SIZE)
            activity.add_buddy_icon(buddy_model.get_buddy().object_path(), icon)

            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def _add_activity(self, activity_model):
        icon = ActivityView(activity_model)
        self._layout.add(icon)

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._activities[activity_model.get_id()] = icon

    def _remove_activity(self, activity_model):
        icon = self._activities[activity_model.get_id()]
        self._layout.remove(icon)
        del self._activities[activity_model.get_id()]
        icon.destroy()

    def add_access_point(self, device, ap):
        icon = AccessPointView(device, ap)
        self._layout.add(icon)

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._access_points[ap.object_path] = icon

    def remove_access_point(self, ap_o):
        icon = self._access_points[ap_o]
        icon.disconnect()
        self._layout.remove(icon)
        del self._access_points[ap_o]

    def suspend(self):
        if not self._suspended:
            self._suspended = True
            for ap in self._access_points.values():
                ap.props.paused = True

    def resume(self):
        if self._suspended:
            self._suspended = False
            for ap in self._access_points.values():
                ap.props.paused = False

    def _toolbar_query_changed_cb(self, toolbar, query):
        self._query = query.lower()
        for icon in self._layout_box.get_children():
            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def focus_search_entry(self):
        self._toolbar.search_entry.grab_focus()
