# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Tomeu Vizoso, Simon Schampijer
# Copyright (C) 2009-2010 One Laptop per Child
# Copyright (C) 2010 Collabora Ltd. <http://www.collabora.co.uk/>
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

from gettext import gettext as _
import logging

import dbus
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gio
from gi.repository import Gtk

from sugar3 import mime
from sugar3.graphics.icon import Icon
from sugar3.graphics.icon import CanvasIcon
from sugar3.graphics import style
from sugar3.graphics.palette import Palette
from sugar3.graphics.palettemenu import PaletteMenuBox
from sugar3.graphics.palettemenu import PaletteMenuItem

from jarabe.model import neighborhood
from jarabe.model.buddy import get_owner_instance
from jarabe.view.buddyicon import BuddyIcon
from jarabe.desktop.snowflakelayout import SnowflakeLayout
from jarabe.desktop.networkviews import WirelessNetworkView
from jarabe.desktop.networkviews import OlpcMeshView
from jarabe.desktop.networkviews import SugarAdhocView
from jarabe.desktop.viewcontainer import ViewContainer
from jarabe.desktop.favoriteslayout import SpreadLayout
from jarabe.util.normalize import normalize_string
from jarabe.model import network
from jarabe.model.network import AccessPoint
from jarabe.model.olpcmesh import OlpcMeshManager
from jarabe.model.adhoc import get_adhoc_manager_instance
from jarabe.journal import journalactivity
from jarabe.journal import misc
from jarabe.journal import peershare
from jarabe.journal import peerview


_FILTERED_ALPHA = 0.33

_BADGE_SCALE = 0.4
_BADGE_INSET = style.zoom(2)


class _ActivityIcon(CanvasIcon):

    def __init__(self, model, file_name, xo_color,
                 size=style.STANDARD_ICON_SIZE, is_joinable=None):
        CanvasIcon.__init__(self, file_name=file_name,
                            xo_color=xo_color, pixel_size=size)

        self._model = model
        self._is_joinable = is_joinable
        self.palette_invoker.props.toggle_palette = True

    def create_palette(self):
        primary_text = self._model.bundle.get_name()
        secondary_text = self._model.get_name()
        palette_icon = Icon(file=self._model.bundle.get_icon(),
                            pixel_size=style.STANDARD_ICON_SIZE,
                            xo_color=self._model.get_color())
        palette = Palette(None,
                          primary_text=primary_text,
                          secondary_text=secondary_text,
                          icon=palette_icon)

        private = self._model.props.private
        joined = get_owner_instance() in self._model.props.buddies
        is_joinable = self._is_joinable is None or self._is_joinable()

        menu_box = PaletteMenuBox()

        if joined:
            item = PaletteMenuItem(_('Resume'))
            icon = Icon(
                pixel_size=style.SMALL_ICON_SIZE, icon_name='activity-start')
            item.set_image(icon)
            item.connect('activate', self.__palette_item_clicked_cb)
            menu_box.append_item(item)
        elif not private and is_joinable:
            item = PaletteMenuItem(_('Join'))
            icon = Icon(
                pixel_size=style.SMALL_ICON_SIZE, icon_name='activity-start')
            item.set_image(icon)
            item.connect('activate', self.__palette_item_clicked_cb)
            menu_box.append_item(item)

        palette.set_content(menu_box)
        menu_box.show_all()

        self.connect_to_palette_pop_events(palette)
        return palette

    def __palette_item_clicked_cb(self, item):
        bundle = self._model.get_bundle()
        misc.launch(bundle, activity_id=self._model.activity_id,
                    color=self._model.get_color())


class _SharedEntryIcon(CanvasIcon):

    def __init__(self, model):
        CanvasIcon.__init__(self, icon_name='activity-journal',
                            xo_color=model.get_color(),
                            pixel_size=style.STANDARD_ICON_SIZE)
        self._model = model
        self._filtered = False
        self._badge = None
        self._badge_size = 0
        self._load_icon()
        # Icons get remade every time entries group and ungroup, but
        # the model sticks around. drop the handlers with the widget or
        # the model keeps the dead icons alive for the whole session.
        self._model_handlers = [
            self._model.connect('notify::name', self.__model_notify_cb),
            self._model.connect('notify::color', self.__model_notify_cb),
            self._model.connect('notify::bundle', self.__bundle_notify_cb),
            self._model.connect('buddy-added', self.__buddy_added_cb),
        ]
        self.connect('destroy', self.__destroy_cb)
        self.palette_invoker.props.toggle_palette = True
        self.palette_invoker.cache_palette = False
        self.connect('activate', self.__activate_cb)

    def get_model(self):
        return self._model

    def __destroy_cb(self, icon):
        for handler in self._model_handlers:
            self._model.disconnect(handler)
        self._model_handlers = []

    def _face(self):
        """(file_name, icon_name) for the entry: the source activity's
        own icon if we have it, else one for the mime type, else the
        Journal's.
        """
        bundle = self._model.get_bundle()
        if bundle is not None:
            return bundle.get_icon(), None
        mime_type = self._model.entry_mime
        if mime_type:
            name = mime.get_mime_icon(mime_type)
            if name and Gtk.IconTheme.get_default().has_icon(name):
                return None, name
        return None, 'activity-journal'

    def _load_icon(self):
        # File_name wins over icon_name in the toolkit's buffer, so
        # clear it when we're using a themed icon. keep the face
        # around, do_draw wants it on every repaint.
        self._face_now = self._face()
        file_name, icon_name = self._face_now
        if file_name is not None:
            self.props.file_name = file_name
        else:
            self.props.file_name = None
            self.props.icon_name = icon_name

    def __activate_cb(self, icon):
        palette = self.get_palette()
        if palette is not None and palette.is_up():
            palette.popdown(immediate=True)
        if peershare.is_ours(self._model.entry_uid):
            # Our own entry, so go to the real page where the sharing
            # switch is
            journal = journalactivity.get_journal()
            journal.reveal()
            journal.show_object(self._model.entry_uid)
            return
        peerview.open_entry(self._model)

    def _secondary_text(self):
        owner = self._model.get_owner()
        nick = owner.get_nick() if owner is not None else ''
        if nick:
            # Isolated so a right to left nick can't reorder the
            # sentence around it
            # TRANS: %s is the name of the friend the entry came from
            return _("From %s's Journal") % ('\u2068%s\u2069' % nick)
        return _('A shared Journal entry')

    def _badge_pixbuf(self):
        """The Journal mark for the corner, at this icon's size.

        The toolkit's badge code hangs badges off theme attach points,
        which a bundle's svg doesn't have, so the badge ends up
        clipped outside the icon. Draw it ourselves instead.
        """
        # Keep the mark even when the face is already the Journal icon,
        # it's the only thing that tells a shared entry from an activity
        size = max(1, int(self.props.pixel_size * _BADGE_SCALE))
        if size != self._badge_size:
            self._badge_size = size
            theme = Gtk.IconTheme.get_default()
            try:
                self._badge = theme.load_icon('activity-journal', size, 0)
            except GLib.Error:
                self._badge = None
        return self._badge

    def do_draw(self, cr):
        CanvasIcon.do_draw(self, cr)
        badge = self._badge_pixbuf()
        if badge is None:
            return
        allocation = self.get_allocation()
        Gdk.cairo_set_source_pixbuf(
            cr, badge,
            allocation.width - badge.get_width() - _BADGE_INSET,
            allocation.height - badge.get_height() - _BADGE_INSET)
        cr.paint()

    def create_palette(self):
        file_name, icon_name = self._face()
        if file_name is not None:
            palette_icon = Icon(file=file_name,
                                pixel_size=style.STANDARD_ICON_SIZE,
                                xo_color=self._model.get_color())
        else:
            palette_icon = Icon(icon_name=icon_name,
                                pixel_size=style.STANDARD_ICON_SIZE,
                                xo_color=self._model.get_color())
        palette = Palette(None,
                          primary_text=self._model.get_name(),
                          secondary_text=self._secondary_text(),
                          icon=palette_icon)
        self.connect_to_palette_pop_events(palette)
        return palette

    def __model_notify_cb(self, model, pspec):
        self._update()

    def __bundle_notify_cb(self, model, pspec):
        # The advert can arrive in pieces, and the source activity is
        # often only named on a later properties signal
        self._load_icon()
        self.queue_draw()

    def __buddy_added_cb(self, model, buddy):
        palette = self.get_palette()
        if palette is not None:
            palette.props.secondary_text = self._secondary_text()

    def _update(self):
        # The advert can arrive in pieces, and a later signal may bring
        # the tags that name a better face
        self._load_icon()
        self.props.xo_color = self._model.get_color()
        if self._filtered:
            self.alpha = _FILTERED_ALPHA
        else:
            self.alpha = 1.0
        palette = self.get_palette()
        if palette is not None:
            palette.props.primary_text = self._model.get_name()
            palette.props.icon.props.xo_color = self._model.get_color()

    def set_filter(self, query):
        name = normalize_string(self._model.get_name() or '')
        self._filtered = name.find(query) == -1
        self._update()


class _SharedEntriesGroup(SnowflakeLayout):

    def __init__(self, owner_model, center_icon):
        SnowflakeLayout.__init__(self)
        self._owner_model = owner_model
        self._center = center_icon
        self._entries = {}
        self.add_icon(center_icon, center=True)
        center_icon.show()

    def get_owner_model(self):
        return self._owner_model

    def do_forall(self, include_internals, callback):
        # GTK walks the children once more during teardown, after the
        # Python side has gone, and by then the wrapper we get has no
        # attributes left. raising here doesn't just fail once. the
        # traceback machinery keeps the dead wrapper alive, then drops
        # it, and the drop runs teardown again, and round it goes. any
        # SnowflakeLayout vfunc that reaches into self._children can
        # hit this, so guard them all and not only the one we saw fire.
        for child in list(getattr(self, '_children', {}).keys()):
            callback(child)

    def do_realize(self):
        self.set_realized(True)
        self.set_window(self.get_parent_window())
        for child in list(getattr(self, '_children', {}).keys()):
            child.set_parent_window(self.get_parent_window())
        self.queue_resize()

    def do_size_allocate(self, allocation):
        if not hasattr(self, '_children'):
            self.set_allocation(allocation)
            return
        SnowflakeLayout.do_size_allocate(self, allocation)

    def _get_radius(self):
        if not hasattr(self, '_children'):
            return 0
        return SnowflakeLayout._get_radius(self)

    def _calculate_size(self):
        if not hasattr(self, '_children'):
            return 0
        return SnowflakeLayout._calculate_size(self)

    def add_entry(self, activity_id, icon):
        self._entries[activity_id] = icon
        self.add_icon(icon)
        icon.show()

    def has_entry(self, activity_id):
        return activity_id in self._entries

    def remove_entry(self, activity_id):
        icon = self._entries.pop(activity_id)
        self.remove(icon)
        icon.destroy()

    def entry_ids(self):
        return list(self._entries.keys())

    def is_empty(self):
        return not self._entries

    def set_filter(self, query):
        self._center.set_filter(query)
        for icon in self._entries.values():
            icon.set_filter(query)

    def get_positioning_data(self):
        return 'entries-of-%s' % (self._owner_model.props.key or '')


class ActivityView(SnowflakeLayout):

    def __init__(self, model):
        SnowflakeLayout.__init__(self)

        self._model = model
        self._model.connect('current-buddy-added', self.__buddy_added_cb)
        self._model.connect('current-buddy-removed', self.__buddy_removed_cb)

        self._icons = {}

        self._icon = self._create_icon()
        self._icon.show()
        self.add_icon(self._icon, center=True)

        self._icon.palette_invoker.cache_palette = False

        for buddy in self._model.props.current_buddies:
            self._add_buddy(buddy)

    def _is_joinable(self):
        max_participants = self._model.bundle.get_max_participants()
        return max_participants == 0 or len(self._icons) < max_participants

    def _create_icon(self):
        icon = _ActivityIcon(self._model,
                             file_name=self._model.bundle.get_icon(),
                             xo_color=self._model.get_color(),
                             size=style.STANDARD_ICON_SIZE,
                             is_joinable=self._is_joinable)
        return icon

    def has_buddy_icon(self, key):
        return key in self._icons

    def __buddy_added_cb(self, activity, buddy):
        self._add_buddy(buddy)

    def _add_buddy(self, buddy):
        icon = BuddyIcon(buddy, style.STANDARD_ICON_SIZE)
        self._icons[buddy.props.key] = icon
        self.add_icon(icon)
        icon.show()

    def __buddy_removed_cb(self, activity, buddy):
        icon = self._icons[buddy.props.key]
        del self._icons[buddy.props.key]
        self.remove(icon)
        icon.destroy()

    def set_filter(self, query):
        text_to_check = self._model.bundle.get_name().lower() + \
            self._model.bundle.get_bundle_id().lower()
        self._icon.props.xo_color = self._model.get_color()
        if text_to_check.find(query) == -1:
            self._icon.alpha = _FILTERED_ALPHA
        else:
            self._icon.alpha = 1.0
        for icon in list(self._icons.values()):
            if hasattr(icon, 'set_filter'):
                icon.set_filter(query)

    def get_positioning_data(self):
        return str(self._model.activity_id)


class DeviceObserver(GObject.GObject):
    __gsignals__ = {
        'access-point-added': (GObject.SignalFlags.RUN_FIRST, None,
                               ([GObject.TYPE_PYOBJECT])),
        'access-point-removed': (GObject.SignalFlags.RUN_FIRST, None,
                                 ([GObject.TYPE_PYOBJECT])),
    }

    def __init__(self, device):
        GObject.GObject.__init__(self)
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
        self._bus.remove_signal_receiver(
            self.__access_point_added_cb,
            signal_name='AccessPointAdded',
            path=self.device.object_path,
            dbus_interface=network.NM_WIRELESS_IFACE)
        self._bus.remove_signal_receiver(
            self.__access_point_removed_cb,
            signal_name='AccessPointRemoved',
            path=self.device.object_path,
            dbus_interface=network.NM_WIRELESS_IFACE)


class NetworkManagerObserver(object):

    _SHOW_ADHOC_CONF_DIR = 'org.sugarlabs.network'
    _SHOW_ADHOC_CONF_KEY = 'adhoc'

    def __init__(self, box):
        self._box = box
        self._bus = None
        self._devices = {}
        self._netmgr = None
        self._olpc_mesh_device_o = None

        settings = Gio.Settings.new(self._SHOW_ADHOC_CONF_DIR)
        self._have_adhoc_networks = \
            settings.get_boolean(self._SHOW_ADHOC_CONF_KEY)

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
        active_connections_o = netmgr_props.Get(network.NM_IFACE,
                                                'ActiveConnections')

        for conn_o in active_connections_o:
            obj = self._bus.get_object(network.NM_IFACE, conn_o)
            props = dbus.Interface(obj, dbus.PROPERTIES_IFACE)
            state = props.Get(network.NM_ACTIVE_CONN_IFACE, 'State')
            if state == network.NM_ACTIVE_CONNECTION_STATE_ACTIVATING:
                ap_o = props.Get(network.NM_ACTIVE_CONN_IFACE,
                                 'SpecificObject')
                found = False
                if ap_o != '/':
                    for net in list(self._box.wireless_networks.values()):
                        if net.find_ap(ap_o) is not None:
                            found = True
                            net.create_keydialog(kwargs['response'])
                if not found:
                    raise Exception(
                        'Could not determine AP for specific object'
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


class MeshBox(ViewContainer):
    __gtype_name__ = 'SugarMeshBox'

    def __init__(self, toolbar):
        logging.debug('STARTUP: Loading the mesh view')

        layout = SpreadLayout()

        # Round off icon size to an even number to ensure that the icon
        owner_icon = BuddyIcon(get_owner_instance(),
                               style.STANDARD_ICON_SIZE & ~1)
        ViewContainer.__init__(self, layout, owner_icon)
        self.set_can_focus(False)

        self.wireless_networks = {}
        self._adhoc_manager = None
        self._adhoc_networks = []

        self._model = neighborhood.get_model()
        self._buddies = {}
        self._activities = {}
        self._entry_groups = {}
        self._mesh = []
        self._buddy_to_activity = {}
        self._suspended = True
        self._query = ''

        toolbar.connect('query-changed', self._toolbar_query_changed_cb)
        toolbar.search_entry.connect('icon-press',
                                     self.__clear_icon_pressed_cb)

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
        if buddy_model.is_owner():
            return
        icon = BuddyIcon(buddy_model)
        self.add(icon)
        icon.show()

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._buddies[buddy_model.props.key] = icon
        self._adopt_entries(buddy_model)

    def _remove_buddy(self, buddy_model):
        logging.debug('MeshBox._remove_buddy')
        key = buddy_model.props.key
        if key in self._entry_groups:
            self._dissolve_group(key, keep_buddy=False)
            return
        icon = self._buddies[key]
        self.remove(icon)
        del self._buddies[key]

    def __buddy_notify_current_activity_cb(self, buddy_model, pspec):
        logging.debug('MeshBox.__buddy_notify_current_activity_cb %s',
                      buddy_model.props.current_activity)
        if buddy_model.props.current_activity is None:
            if buddy_model.props.key not in self._buddies:
                self._add_buddy(buddy_model)
        elif buddy_model.props.key in self._buddies:
            self._remove_buddy(buddy_model)

    def _add_activity(self, activity_model):
        if activity_model.entry_uid is not None:
            activity_model.connect('notify::owner',
                                   self.__entry_owner_notify_cb)
            icon = _SharedEntryIcon(activity_model)
            group = self._group_for(activity_model)
            if group is not None:
                group.add_entry(activity_model.activity_id, icon)
            else:
                self.add(icon)
                icon.show()
            icon.set_filter(self._query)
            self._activities[activity_model.activity_id] = icon
            return
        icon = ActivityView(activity_model)
        self.add(icon)
        icon.show()

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._activities[activity_model.activity_id] = icon

    def _remove_activity(self, activity_model):
        activity_id = activity_model.activity_id
        icon = self._activities.pop(activity_id)
        for key, group in list(self._entry_groups.items()):
            if group.has_entry(activity_id):
                group.remove_entry(activity_id)
                if group.is_empty():
                    self._dissolve_group(key, keep_buddy=True)
                return
        self.remove(icon)
        if isinstance(icon, _SharedEntryIcon):
            # Its model handlers only come off on destroy
            icon.destroy()

    def _group_for(self, activity_model):
        """The snowflake around this entry's owner, made if it isn't
        there yet. None if the owner has no icon of their own to
        gather around.
        """
        owner = activity_model.get_owner()
        if owner is None or owner.is_owner():
            return None
        key = owner.props.key
        group = self._entry_groups.get(key)
        if group is not None:
            return group
        if key not in self._buddies:
            return None
        old = self._buddies.pop(key)
        self.remove(old)
        old.destroy()
        group = _SharedEntriesGroup(owner, BuddyIcon(owner))
        self.add(group)
        group.show()
        group.set_filter(self._query)
        self._entry_groups[key] = group
        self._buddies[key] = group
        return group

    def _dissolve_group(self, key, keep_buddy):
        group = self._entry_groups.pop(key)
        owner_model = group.get_owner_model()
        leftovers = [(activity_id,
                      self._activities[activity_id].get_model())
                     for activity_id in group.entry_ids()
                     if activity_id in self._activities]
        self.remove(group)
        group.destroy()
        del self._buddies[key]
        if keep_buddy:
            icon = BuddyIcon(owner_model)
            self.add(icon)
            icon.show()
            icon.set_filter(self._query)
            self._buddies[key] = icon
        for activity_id, model in leftovers:
            icon = _SharedEntryIcon(model)
            self.add(icon)
            icon.show()
            icon.set_filter(self._query)
            self._activities[activity_id] = icon

    def _adopt_entries(self, buddy_model):
        for activity_model in self._model.get_activities():
            if activity_model.entry_uid is not None and \
                    activity_model.get_owner() is buddy_model:
                self.__entry_owner_notify_cb(activity_model, None)

    def __entry_owner_notify_cb(self, activity_model, pspec):
        activity_id = activity_model.activity_id
        icon = self._activities.get(activity_id)
        if icon is None:
            return
        if any(group.has_entry(activity_id)
               for group in self._entry_groups.values()):
            return
        group = self._group_for(activity_model)
        if group is None:
            return
        self.remove(icon)
        icon.destroy()
        fresh = _SharedEntryIcon(activity_model)
        group.add_entry(activity_id, fresh)
        fresh.set_filter(self._query)
        self._activities[activity_id] = fresh

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
            self.add(icon)
            icon.show()
            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def _remove_net_if_empty(self, net, hash_value):
        # remove a network if it has no APs left
        if net.num_aps() == 0:
            net.disconnect()
            self.remove(net)
            del self.wireless_networks[hash_value]

    def _ap_props_changed_cb(self, ap, old_hash_value):
        # if we have mesh hardware, ignore OLPC mesh networks that appear as
        # normal wifi networks
        if len(self._mesh) > 0 and ap.mode == network.NM_802_11_MODE_ADHOC \
                and ap.ssid == b'olpc-mesh':
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
            if hash_value in self.wireless_networks:
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
        for net in list(self.wireless_networks.values()):
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
            self.remove(icon)
        self._adhoc_networks = []
        self._adhoc_manager.stop_listening()

    def _add_adhoc_network_icon(self, channel):
        icon = SugarAdhocView(channel)
        self.add(icon)
        icon.show()
        self._adhoc_networks.append(icon)

    def _add_olpc_mesh_icon(self, mesh_mgr, channel):
        icon = OlpcMeshView(mesh_mgr, channel)
        self.add(icon)
        icon.show()
        self._mesh.append(icon)

    def enable_olpc_mesh(self, mesh_device):
        mesh_mgr = OlpcMeshManager(mesh_device)
        self._add_olpc_mesh_icon(mesh_mgr, 1)
        self._add_olpc_mesh_icon(mesh_mgr, 6)
        self._add_olpc_mesh_icon(mesh_mgr, 11)

        # the OLPC mesh can be recognised as a "normal" wifi network. remove
        # any such normal networks if they have been created
        for hash_value, net in list(self.wireless_networks.items()):
            if not net.is_olpc_mesh():
                continue

            logging.debug('removing OLPC mesh IBSS')
            net.remove_all_aps()
            net.disconnect()
            self.remove(net)
            del self.wireless_networks[hash_value]

    def disable_olpc_mesh(self, mesh_device):
        for icon in self._mesh:
            icon.disconnect()
            self.remove(icon)
        self._mesh = []

    def suspend(self):
        if not self._suspended:
            self._suspended = True
            for net in list(self.wireless_networks.values()) + self._mesh:
                net.props.paused = True

    def resume(self):
        if self._suspended:
            self._suspended = False
            for net in list(self.wireless_networks.values()) + self._mesh:
                net.props.paused = False

    def _toolbar_query_changed_cb(self, toolbar, query):
        self._query = normalize_string(query)
        for icon in self.get_children():
            if hasattr(icon, 'set_filter'):
                icon.set_filter(self._query)

    def __clear_icon_pressed_cb(self, entry, icon_pos, event):
        self.grab_focus()
