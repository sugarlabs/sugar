# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009-2010 One Laptop per Child
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

import dbus
import hippo
import glib
import gobject
import gtk
import gconf

from sugar.graphics.icon import CanvasIcon, Icon
from sugar.graphics import style
from sugar.graphics import palette
from sugar.graphics import iconentry
from sugar.graphics.menuitem import MenuItem

from jarabe.model import neighborhood
from jarabe.model.buddy import get_owner_instance
from jarabe.view.buddyicon import BuddyIcon
from jarabe.desktop.snowflakelayout import SnowflakeLayout
from jarabe.desktop.spreadlayout import SpreadLayout
from jarabe.desktop.networkviews import WirelessNetworkView
from jarabe.desktop.networkviews import OlpcMeshView
from jarabe.desktop.networkviews import SugarAdhocView
from jarabe.model import network
from jarabe.model.network import AccessPoint
from jarabe.model.olpcmesh import OlpcMeshManager
from jarabe.model.adhoc import get_adhoc_manager_instance
from jarabe.journal import misc


_AP_ICON_NAME = 'network-wireless'
_OLPC_MESH_ICON_NAME = 'network-mesh'

_AUTOSEARCH_TIMEOUT = 1000
_FILTERED_ALPHA = 0.33


class _ActivityIcon(CanvasIcon):
    def __init__(self, model, file_name, xo_color,
                 size=style.STANDARD_ICON_SIZE):
        CanvasIcon.__init__(self, file_name=file_name,
                            xo_color=xo_color,
                            size=size)
        self._model = model
        self.connect('activated', self._clicked_cb)

    def create_palette(self):
        primary_text = glib.markup_escape_text(self._model.bundle.get_name())
        secondary_text = glib.markup_escape_text(self._model.get_name())
        p_icon = Icon(file=self._model.bundle.get_icon(),
                      xo_color=self._model.get_color())
        p_icon.props.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
        p = palette.Palette(None,
                            primary_text=primary_text,
                            secondary_text=secondary_text,
                            icon=p_icon)

        private = self._model.props.private
        joined = get_owner_instance() in self._model.props.buddies

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

    def _clicked_cb(self, item):
        bundle = self._model.get_bundle()
        misc.launch(bundle, activity_id=self._model.activity_id,
                    color=self._model.get_color())


class ActivityView(hippo.CanvasBox):
    def __init__(self, model):
        hippo.CanvasBox.__init__(self)

        self._model = model
        self._model.connect('current-buddy-added', self.__buddy_added_cb)
        self._model.connect('current-buddy-removed', self.__buddy_removed_cb)

        self._icons = {}

        self._layout = SnowflakeLayout()
        self.set_layout(self._layout)

        self._icon = self._create_icon()
        self._layout.add(self._icon, center=True)

        self._icon.palette_invoker.cache_palette = False

        for buddy in self._model.props.current_buddies:
            self._add_buddy(buddy)

    def _create_icon(self):
        icon = _ActivityIcon(self._model,
                             file_name=self._model.bundle.get_icon(),
                             xo_color=self._model.get_color(),
                             size=style.STANDARD_ICON_SIZE)
        return icon

    def has_buddy_icon(self, key):
        return key in self._icons

    def __buddy_added_cb(self, activity, buddy):
        self._add_buddy(buddy)

    def _add_buddy(self, buddy):
        icon = BuddyIcon(buddy, style.STANDARD_ICON_SIZE)
        self._icons[buddy.props.key] = icon
        self._layout.add(icon)

    def __buddy_removed_cb(self, activity, buddy):
        icon = self._icons[buddy.props.key]
        del self._icons[buddy.props.key]
        icon.destroy()

    def set_filter(self, query):
        text_to_check = self._model.bundle.get_name().lower() + \
                self._model.bundle.get_bundle_id().lower()
        self._icon.props.xo_color = self._model.get_color()
        if text_to_check.find(query) == -1:
            self._icon.alpha = _FILTERED_ALPHA
        else:
            self._icon.alpha = 1.0
        for icon in self._icons.itervalues():
            if hasattr(icon, 'set_filter'):
                icon.set_filter(query)


class MeshToolbar(gtk.Toolbar):
    __gtype_name__ = 'MeshToolbar'

    __gsignals__ = {
        'query-changed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                          ([str])),
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


class DeviceObserver(gobject.GObject):
    __gsignals__ = {
        'access-point-added': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                               ([gobject.TYPE_PYOBJECT])),
        'access-point-removed': (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,
                                 ([gobject.TYPE_PYOBJECT])),
    }

    def __init__(self, device):
        gobject.GObject.__init__(self)
        self._bus = dbus.SystemBus()
        self.device = device

        wireless = dbus.Interface(device, network.NM_WIRELESS_IFACE)
        wireless.GetAccessPoints(
            reply_handler=self._get_access_points_reply_cb,
            error_handler=self._get_access_points_error_cb)

        self._bus.add_signal_receiver(self.__access_point_added_cb,
                                      signal_name='AccessPointAdded',
                                      path=device.object_path,
                                      dbus_interface=network.NM_WIRELESS_IFACE)
        self._bus.add_signal_receiver(self.__access_point_removed_cb,
                                      signal_name='AccessPointRemoved',
                                      path=device.object_path,
                                      dbus_interface=network.NM_WIRELESS_IFACE)

    def _get_access_points_reply_cb(self, access_points_o):
        for ap_o in access_points_o:
            ap = self._bus.get_object(network.NM_SERVICE, ap_o)
            self.emit('access-point-added', ap)

    def _get_access_points_error_cb(self, err):
        logging.error('Failed to get access points: %s', err)

    def __access_point_added_cb(self, access_point_o):
        ap = self._bus.get_object(network.NM_SERVICE, access_point_o)
        self.emit('access-point-added', ap)

    def __access_point_removed_cb(self, access_point_o):
        self.emit('access-point-removed', access_point_o)

    def disconnect(self):
        self._bus.remove_signal_receiver(self.__access_point_added_cb,
                                         signal_name='AccessPointAdded',
                                         path=self.device.object_path,
                                         dbus_interface=network.NM_WIRELESS_IFACE)
        self._bus.remove_signal_receiver(self.__access_point_removed_cb,
                                         signal_name='AccessPointRemoved',
                                         path=self.device.object_path,
                                         dbus_interface=network.NM_WIRELESS_IFACE)


class NetworkManagerObserver(object):

    _SHOW_ADHOC_GCONF_KEY = '/desktop/sugar/network/adhoc'

    def __init__(self, box):
        self._box = box
        self._bus = None
        self._devices = {}
        self._netmgr = None
        self._olpc_mesh_device_o = None

        client = gconf.client_get_default()
        self._have_adhoc_networks = client.get_bool(self._SHOW_ADHOC_GCONF_KEY)

    def listen(self):
        try:
            self._bus = dbus.SystemBus()
            self._netmgr = network.get_manager()
        except dbus.DBusException:
            logging.debug('NetworkManager not available')
            return

        self._netmgr.GetDevices(reply_handler=self.__get_devices_reply_cb,
                                error_handler=self.__get_devices_error_cb)

        self._bus.add_signal_receiver(self.__device_added_cb,
                                      signal_name='DeviceAdded',
                                      dbus_interface=network.NM_IFACE)
        self._bus.add_signal_receiver(self.__device_removed_cb,
                                      signal_name='DeviceRemoved',
                                      dbus_interface=network.NM_IFACE)
        self._bus.add_signal_receiver(self.__properties_changed_cb,
                                      signal_name='PropertiesChanged',
                                      dbus_interface=network.NM_IFACE)

        secret_agent = network.get_secret_agent()
        if secret_agent is not None:
            secret_agent.secrets_request.connect(self.__secrets_request_cb)

    def __secrets_request_cb(self, **kwargs):
        # FIXME It would be better to do all of this async, but I cannot think
        # of a good way to. NM could really use some love here.

        netmgr_props = dbus.Interface(self._netmgr, dbus.PROPERTIES_IFACE)
        active_connections_o = netmgr_props.Get(network.NM_IFACE, 'ActiveConnections')

        for conn_o in active_connections_o:
            obj = self._bus.get_object(network.NM_IFACE, conn_o)
            props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            state = props.Get(network.NM_ACTIVE_CONN_IFACE, 'State')
            if state == network.NM_ACTIVE_CONNECTION_STATE_ACTIVATING:
                ap_o = props.Get(network.NM_ACTIVE_CONN_IFACE, 'SpecificObject')
                found = False
                if ap_o != '/':
                    for net in self._box.wireless_networks.values():
                        if net.find_ap(ap_o) is not None:
                            found = True
                            net.create_keydialog(kwargs['response'])
                if not found:
                    raise Exception('Could not determine AP for specific object'
                                    ' %s' % conn_o)

    def __get_devices_reply_cb(self, devices_o):
        for dev_o in devices_o:
            self._check_device(dev_o)

    def __get_devices_error_cb(self, err):
        logging.error('Failed to get devices: %s', err)

    def _check_device(self, device_o):
        device = self._bus.get_object(network.NM_SERVICE, device_o)
        props = dbus.Interface(device, dbus.PROPERTIES_IFACE)

        device_type = props.Get(network.NM_DEVICE_IFACE, 'DeviceType')
        if device_type == network.NM_DEVICE_TYPE_WIFI:
            if device_o in self._devices:
                return
            self._devices[device_o] = DeviceObserver(device)
            self._devices[device_o].connect('access-point-added',
                                            self.__ap_added_cb)
            self._devices[device_o].connect('access-point-removed',
                                            self.__ap_removed_cb)
            if self._have_adhoc_networks:
                self._box.add_adhoc_networks(device)
        elif device_type == network.NM_DEVICE_TYPE_OLPC_MESH:
            if device_o == self._olpc_mesh_device_o:
                return
            self._olpc_mesh_device_o = device_o
            self._box.enable_olpc_mesh(device)

    def _get_device_path_error_cb(self, err):
        logging.error('Failed to get device type: %s', err)

    def __device_added_cb(self, device_o):
        self._check_device(device_o)

    def __device_removed_cb(self, device_o):
        if device_o in self._devices:
            observer = self._devices[device_o]
            observer.disconnect()
            del self._devices[device_o]
            if self._have_adhoc_networks:
                self._box.remove_adhoc_networks()
            return

        if self._olpc_mesh_device_o == device_o:
            self._box.disable_olpc_mesh(device_o)
            self._olpc_mesh_device_o = None

    def __ap_added_cb(self, device_observer, access_point):
        self._box.add_access_point(device_observer.device, access_point)

    def __ap_removed_cb(self, device_observer, access_point_o):
        self._box.remove_access_point(access_point_o)

    def __properties_changed_cb(self, properties):
        if 'WirelessHardwareEnabled' in properties:
            if properties['WirelessHardwareEnabled']:
                if not self._have_adhoc_networks:
                    self._box.remove_adhoc_networks()
            elif properties['WirelessHardwareEnabled']:
                for device in self._devices:
                    if self._have_adhoc_networks:
                        self._box.add_adhoc_networks(device)


class MeshBox(gtk.VBox):
    __gtype_name__ = 'SugarMeshBox'

    def __init__(self):
        logging.debug('STARTUP: Loading the mesh view')

        gobject.GObject.__init__(self)

        self.wireless_networks = {}
        self._adhoc_manager = None
        self._adhoc_networks = []

        self._model = neighborhood.get_model()
        self._buddies = {}
        self._activities = {}
        self._mesh = []
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
            self._add_buddy(buddy_model)

        self._model.connect('buddy-added', self._buddy_added_cb)
        self._model.connect('buddy-removed', self._buddy_removed_cb)

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
        self._add_buddy(buddy_model)

    def _buddy_removed_cb(self, model, buddy_model):
        self._remove_buddy(buddy_model)

    def _activity_added_cb(self, model, activity_model):
        self._add_activity(activity_model)

    def _activity_removed_cb(self, model, activity_model):
        self._remove_activity(activity_model)

    def _add_buddy(self, buddy_model):
        buddy_model.connect('notify::current-activity',
                            self.__buddy_notify_current_activity_cb)
        if buddy_model.props.current_activity is not None:
            return
        icon = BuddyIcon(buddy_model)
        if buddy_model.is_owner():
            self._owner_icon = icon
        self._layout.add(icon)

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._buddies[buddy_model.props.key] = icon

    def _remove_buddy(self, buddy_model):
        logging.debug('MeshBox._remove_buddy')
        icon = self._buddies[buddy_model.props.key]
        self._layout.remove(icon)
        del self._buddies[buddy_model.props.key]
        icon.destroy()

    def __buddy_notify_current_activity_cb(self, buddy_model, pspec):
        logging.debug('MeshBox.__buddy_notify_current_activity_cb %s',
                      buddy_model.props.current_activity)
        if buddy_model.props.current_activity is None:
            if not buddy_model.props.key in self._buddies:
                self._add_buddy(buddy_model)
        elif buddy_model.props.key in self._buddies:
            self._remove_buddy(buddy_model)

    def _add_activity(self, activity_model):
        icon = ActivityView(activity_model)
        self._layout.add(icon)

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._activities[activity_model.activity_id] = icon

    def _remove_activity(self, activity_model):
        icon = self._activities[activity_model.activity_id]
        self._layout.remove(icon)
        del self._activities[activity_model.activity_id]
        icon.destroy()

    # add AP to its corresponding network icon on the desktop,
    # creating one if it doesn't already exist
    def _add_ap_to_network(self, ap):
        hash_value = ap.network_hash()
        if hash_value in self.wireless_networks:
            self.wireless_networks[hash_value].add_ap(ap)
        else:
            # this is a new network
            icon = WirelessNetworkView(ap)
            self.wireless_networks[hash_value] = icon
            self._layout.add(icon)
            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def _remove_net_if_empty(self, net, hash_value):
        # remove a network if it has no APs left
        if net.num_aps() == 0:
            net.disconnect()
            self._layout.remove(net)
            del self.wireless_networks[hash_value]

    def _ap_props_changed_cb(self, ap, old_hash_value):
        # if we have mesh hardware, ignore OLPC mesh networks that appear as
        # normal wifi networks
        if len(self._mesh) > 0 and ap.mode == network.NM_802_11_MODE_ADHOC \
                and ap.ssid == 'olpc-mesh':
            logging.debug('ignoring OLPC mesh IBSS')
            ap.disconnect()
            return

        if self._adhoc_manager is not None and \
                network.is_sugar_adhoc_network(ap.ssid) and \
                ap.mode == network.NM_802_11_MODE_ADHOC:
            if old_hash_value is None:
                # new Ad-hoc network finished initializing
                self._adhoc_manager.add_access_point(ap)
            # we are called as well in other cases but we do not need to
            # act here as we don't display signal strength for Ad-hoc networks
            return

        if old_hash_value is None:
            # new AP finished initializing
            self._add_ap_to_network(ap)
            return

        hash_value = ap.network_hash()
        if old_hash_value == hash_value:
            # no change in network identity, so just update signal strengths
            self.wireless_networks[hash_value].update_strength()
            return

        # properties change includes a change of the identity of the network
        # that it is on. so create this as a new network.
        self.wireless_networks[old_hash_value].remove_ap(ap)
        self._remove_net_if_empty(self.wireless_networks[old_hash_value],
            old_hash_value)
        self._add_ap_to_network(ap)

    def add_access_point(self, device, ap_o):
        ap = AccessPoint(device, ap_o)
        ap.connect('props-changed', self._ap_props_changed_cb)
        ap.initialize()

    def remove_access_point(self, ap_o):
        if self._adhoc_manager is not None:
            if self._adhoc_manager.is_sugar_adhoc_access_point(ap_o):
                self._adhoc_manager.remove_access_point(ap_o)
                return

        # we don't keep an index of ap object path to network, but since
        # we'll only ever have a handful of networks, just try them all...
        for net in self.wireless_networks.values():
            ap = net.find_ap(ap_o)
            if not ap:
                continue

            ap.disconnect()
            net.remove_ap(ap)
            self._remove_net_if_empty(net, ap.network_hash())
            return

        # it's not an error if the AP isn't found, since we might have ignored
        # it (e.g. olpc-mesh adhoc network)
        logging.debug('Can not remove access point %s', ap_o)

    def add_adhoc_networks(self, device):
        if self._adhoc_manager is None:
            self._adhoc_manager = get_adhoc_manager_instance()
        self._adhoc_manager.start_listening(device)
        self._add_adhoc_network_icon(1)
        self._add_adhoc_network_icon(6)
        self._add_adhoc_network_icon(11)
        self._adhoc_manager.autoconnect()

    def remove_adhoc_networks(self):
        for icon in self._adhoc_networks:
            self._layout.remove(icon)
        self._adhoc_networks = []
        self._adhoc_manager.stop_listening()

    def _add_adhoc_network_icon(self, channel):
        icon = SugarAdhocView(channel)
        self._layout.add(icon)
        self._adhoc_networks.append(icon)

    def _add_olpc_mesh_icon(self, mesh_mgr, channel):
        icon = OlpcMeshView(mesh_mgr, channel)
        self._layout.add(icon)
        self._mesh.append(icon)

    def enable_olpc_mesh(self, mesh_device):
        mesh_mgr = OlpcMeshManager(mesh_device)
        self._add_olpc_mesh_icon(mesh_mgr, 1)
        self._add_olpc_mesh_icon(mesh_mgr, 6)
        self._add_olpc_mesh_icon(mesh_mgr, 11)

        # the OLPC mesh can be recognised as a "normal" wifi network. remove
        # any such normal networks if they have been created
        for hash_value, net in self.wireless_networks.iteritems():
            if not net.is_olpc_mesh():
                continue

            logging.debug('removing OLPC mesh IBSS')
            net.remove_all_aps()
            net.disconnect()
            self._layout.remove(net)
            del self.wireless_networks[hash_value]

    def disable_olpc_mesh(self, mesh_device):
        for icon in self._mesh:
            icon.disconnect()
            self._layout.remove(icon)
        self._mesh = []

    def suspend(self):
        if not self._suspended:
            self._suspended = True
            for net in self.wireless_networks.values() + self._mesh:
                net.props.paused = True

    def resume(self):
        if self._suspended:
            self._suspended = False
            for net in self.wireless_networks.values() + self._mesh:
                net.props.paused = False

    def _toolbar_query_changed_cb(self, toolbar, query):
        self._query = query.lower()
        for icon in self._layout_box.get_children():
            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def focus_search_entry(self):
        self._toolbar.search_entry.grab_focus()
