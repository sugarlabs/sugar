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

import hippo
import gobject
import gtk

from sugar.graphics.icon import CanvasIcon, Icon
from sugar.graphics.xocolor import XoColor
from sugar.graphics import style
from sugar.graphics.icon import get_icon_state
from sugar.graphics import palette
from sugar.graphics import iconentry
from sugar.graphics.menuitem import MenuItem
from sugar import profile

from jarabe.model import accesspointmodel
from jarabe.model.devices import wireless
from jarabe.model import shellmodel
from jarabe.hardware import hardwaremanager
from jarabe.hardware import nmclient
from jarabe.view.buddyicon import BuddyIcon
from jarabe.view.pulsingicon import CanvasPulsingIcon
from jarabe.desktop.snowflakelayout import SnowflakeLayout
from jarabe.desktop.spreadlayout import SpreadLayout
from jarabe.view import shell

from jarabe.hardware.nmclient import NM_802_11_CAP_PROTO_WEP, \
    NM_802_11_CAP_PROTO_WPA, NM_802_11_CAP_PROTO_WPA2


_ICON_NAME = 'network-wireless'

class AccessPointView(CanvasPulsingIcon):
    def __init__(self, model, mesh_device=None):
        CanvasPulsingIcon.__init__(self, size=style.STANDARD_ICON_SIZE,
                                   cache=True)
        self._model = model
        self._meshdev = mesh_device
        self._disconnect_item = None
        self._connect_item = None
        self._greyed_out = False

        self.connect('activated', self._activate_cb)

        model.connect('notify::strength', self._strength_changed_cb)
        model.connect('notify::name', self._name_changed_cb)
        model.connect('notify::state', self._state_changed_cb)

        pulse_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                         style.COLOR_TRANSPARENT.get_svg()))
        self.props.pulse_color = pulse_color

        # Update badge
        caps = model.props.capabilities
        if model.get_nm_network().is_favorite():
            self.props.badge_name = "emblem-favorite"
        elif (caps & NM_802_11_CAP_PROTO_WEP) or \
                (caps & NM_802_11_CAP_PROTO_WPA) or \
                (caps & NM_802_11_CAP_PROTO_WPA2):
            self.props.badge_name = "emblem-locked"

        self._palette = self._create_palette()
        self.set_palette(self._palette)

        self._update_icon()
        self._update_name()
        self._update_state()

    def _create_palette(self):
        icon_name = get_icon_state(_ICON_NAME, self._model.props.strength)
        palette_icon = Icon(icon_name=icon_name,
                            icon_size=style.STANDARD_ICON_SIZE,
                            badge_name=self.props.badge_name)
        ap_color = self._model.get_nm_network().get_colors()
        palette_icon.props.xo_color = XoColor('%s,%s' % ap_color)
                                              
        p = palette.Palette(primary_text=self._model.props.name,
                            icon=palette_icon)

        self._connect_item = MenuItem(_('Connect'), 'dialog-ok')
        self._connect_item.connect('activate', self._activate_cb)
        p.menu.append(self._connect_item)

        # Only show disconnect when there's a mesh device, because mesh takes
        # priority over the normal wireless device. NM doesn't have a
        # "disconnect" method for a device either (for various reasons)
        # so this doesn't have a good mapping
        if self._meshdev:
            self._disconnect_item = MenuItem(_('Disconnect'), 'media-eject')
            self._disconnect_item.connect('activate',
                                          self._disconnect_activate_cb)
            p.menu.append(self._disconnect_item)

        return p

    def _disconnect_activate_cb(self, menuitem):
        # Disconnection for an AP means activating the default mesh device
        network_manager = hardwaremanager.get_network_manager()
        if network_manager and self._meshdev:
            network_manager.set_active_device(self._meshdev)
            self._palette.props.secondary_text = _('Disconnecting...')
            self.props.pulsing = False

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()

    def _name_changed_cb(self, model, pspec):
        self._update_name()

    def _state_changed_cb(self, model, pspec):
        self._update_icon()
        self._update_state()

    def _activate_cb(self, icon):
        network_manager = hardwaremanager.get_network_manager()
        if network_manager:
            device = self._model.get_nm_device()
            network = self._model.get_nm_network()
            network_manager.set_active_device(device, network)

    def _update_name(self):
        self._palette.props.primary_text = self._model.props.name

    def _update_icon(self):
        # keep this code in sync with view/devices/network/wireless.py
        strength = self._model.props.strength
        if self._model.props.state == accesspointmodel.STATE_CONNECTED:
            icon_name = '%s-connected' % _ICON_NAME
        else:
            icon_name = _ICON_NAME
        icon_name = get_icon_state(icon_name, strength)
        if icon_name:
            self.props.icon_name = icon_name
            icon = self._palette.props.icon
            icon.props.icon_name = icon_name

    def _update_state(self):
        if self._model.props.state == accesspointmodel.STATE_CONNECTING:
            if self._disconnect_item:
                self._disconnect_item.show()
            self._connect_item.hide()
            self._palette.props.secondary_text = _('Connecting...')
            self.props.pulsing = True
        elif self._model.props.state == accesspointmodel.STATE_CONNECTED:
            if self._disconnect_item:
                self._disconnect_item.show()
            self._connect_item.hide()
            # TODO: show the channel number
            self._palette.props.secondary_text = _('Connected')
            self.props.pulsing = False
        elif self._model.props.state == accesspointmodel.STATE_NOTCONNECTED:
            if self._disconnect_item:
                self._disconnect_item.hide()
            self._connect_item.show()
            # TODO: show the channel number
            self._palette.props.secondary_text = None
            self.props.pulsing = False

        if self._greyed_out:
            self.props.pulsing = False
            self.props.base_color = XoColor('#D5D5D5,#D5D5D5')
        else:
            self.props.base_color = XoColor('%s,%s' % \
                    self._model.get_nm_network().get_colors())

    def set_filter(self, query):
        self._greyed_out = self._model.props.name.lower().find(query) == -1
        self._update_state()

_MESH_ICON_NAME = 'network-mesh'

class MeshDeviceView(CanvasPulsingIcon):
    def __init__(self, nm_device, channel):
        if not channel in [1, 6, 11]:
            raise ValueError("Invalid channel %d" % channel)

        CanvasPulsingIcon.__init__(self, size=style.STANDARD_ICON_SIZE,
                             icon_name=_MESH_ICON_NAME, cache=True)

        self._nm_device = nm_device
        self.channel = channel
        self.props.badge_name = "badge-channel-%d" % self.channel
        self._greyed_out = False

        self._disconnect_item = None
        self._palette = self._create_palette()
        self.set_palette(self._palette)

        pulse_color = XoColor('%s,%s' % (style.COLOR_BUTTON_GREY.get_svg(),
                                         style.COLOR_TRANSPARENT.get_svg()))
        self.props.pulse_color = pulse_color

        self.connect('activated', self._activate_cb)

        self._nm_device.connect('state-changed', self._state_changed_cb)
        self._nm_device.connect('activation-stage-changed',
                                self._state_changed_cb)
        self._update_state()

    def _create_palette(self):
        p = palette.Palette(_("Mesh Network") + " " + str(self.channel),
                            menu_after_content=True)

        self._disconnect_item = gtk.MenuItem(_('Disconnect...'))
        self._disconnect_item.connect('activate', self._disconnect_activate_cb)
        p.menu.append(self._disconnect_item)

        state = self._nm_device.get_state()
        chan = wireless.freq_to_channel(self._nm_device.get_frequency())
        if state == nmclient.DEVICE_STATE_ACTIVATED and chan == self.channel:
            self._disconnect_item.show()
        return p

    def _disconnect_activate_cb(self, menuitem):
        network_manager = hardwaremanager.get_network_manager()
        if network_manager:
            network_manager.set_active_device(self._nm_device)

    def _activate_cb(self, icon):
        network_manager = hardwaremanager.get_network_manager()
        if network_manager:
            freq = wireless.channel_to_freq(self.channel)
            network_manager.set_active_device(self._nm_device, mesh_freq=freq)

    def _state_changed_cb(self, model):
        self._update_state()

    def _update_state(self):
        state = self._nm_device.get_state()
        chan = wireless.freq_to_channel(self._nm_device.get_frequency())
        if state == nmclient.DEVICE_STATE_ACTIVATING and chan == self.channel:
            self._disconnect_item.hide()
            self.props.pulsing = True
        elif state == nmclient.DEVICE_STATE_ACTIVATED and chan == self.channel:
            self._disconnect_item.show()
            self.props.pulsing = False
        elif state == nmclient.DEVICE_STATE_INACTIVE or chan != self.channel:
            self._disconnect_item.hide()
            self.props.pulsing = False

        if self._greyed_out:
            self.props.pulsing = False
            self.props.base_color = XoColor('#D5D5D5,#D5D5D5')
        else:
            self.props.base_color = profile.get_color()

    def set_filter(self, query):
        self._greyed_out = (query != '')
        self._update_state()

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
        shell.get_instance().join_activity(bundle_id, self._model.get_id())

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
        logging.debug('ActivityView._joined_changed_cb: AAAA!!!!')

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

class MeshBox(gtk.VBox):
    __gtype_name__ = 'SugarMeshBox'
    def __init__(self):
        gobject.GObject.__init__(self)

        self._model = shellmodel.get_instance().get_mesh()
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

        for ap_model in self._model.get_access_points():
            self._add_access_point(ap_model)

        self._model.connect('access-point-added',
                            self._access_point_added_cb)
        self._model.connect('access-point-removed',
                            self._access_point_removed_cb)

        if self._model.get_mesh():
            self.__mesh_added_cb(self._model, self._model.get_mesh())

        self._model.connect('mesh-added', self.__mesh_added_cb)
        self._model.connect('mesh-removed', self.__mesh_removed_cb)

    def __mesh_added_cb(self, model, meshdev):
        self._add_mesh_icon(meshdev, 1)
        self._add_mesh_icon(meshdev, 6)
        self._add_mesh_icon(meshdev, 11)

    def __mesh_removed_cb(self, model):
        self._remove_mesh_icon(1)
        self._remove_mesh_icon(6)
        self._remove_mesh_icon(11)

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

    def _add_mesh_icon(self, meshdev, channel):
        if self._mesh.has_key(channel):
            self._remove_mesh_icon(channel)
        if not meshdev:
            return
        self._mesh[channel] = MeshDeviceView(meshdev, channel)
        self._layout.add(self._mesh[channel])

    def _remove_mesh_icon(self, channel):
        if not self._mesh.has_key(channel):
            return
        self._layout.remove(self._mesh[channel])
        del self._mesh[channel]

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

    def _add_access_point(self, ap_model):
        meshdev = self._model.get_mesh()
        icon = AccessPointView(ap_model, meshdev)
        self._layout.add(icon)

        if hasattr(icon, 'set_filter'):
            icon.set_filter(self._query)

        self._access_points[ap_model.get_id()] = icon

    def _remove_access_point(self, ap_model):
        icon = self._access_points[ap_model.get_id()]
        self._layout.remove(icon)
        del self._access_points[ap_model.get_id()]

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
