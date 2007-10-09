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

import random

import hippo
import gobject
import gtk
from gettext import gettext as _

from sugar.graphics.spreadlayout import SpreadLayout
from sugar.graphics.icon import CanvasIcon
from sugar.graphics import style
from sugar.graphics import xocolor
from sugar.graphics.icon import get_icon_state
from sugar.graphics import style
from sugar.graphics import palette
from sugar import profile

from model import accesspointmodel
from model.devices.network import mesh
from model.devices.network import wireless
from hardware import hardwaremanager
from hardware import nmclient
from view.BuddyIcon import BuddyIcon
from view.pulsingicon import PulsingIcon
from view.home.snowflakelayout import SnowflakeLayout

from hardware.nmclient import NM_802_11_CAP_PROTO_WEP, NM_802_11_CAP_PROTO_WPA, NM_802_11_CAP_PROTO_WPA2


_ICON_NAME = 'network-wireless'

class AccessPointView(PulsingIcon):
    def __init__(self, model, mesh_device=None):
        PulsingIcon.__init__(self, size=style.STANDARD_ICON_SIZE, cache=True)
        self._model = model
        self._meshdev = mesh_device
        self._disconnect_item = None

        self.connect('activated', self._activate_cb)

        model.connect('notify::strength', self._strength_changed_cb)
        model.connect('notify::name', self._name_changed_cb)
        model.connect('notify::state', self._state_changed_cb)

        (stroke, fill) = model.get_nm_network().get_colors()
        self._device_stroke = stroke
        self._device_fill = fill

        self._palette = self._create_palette()
        self.set_palette(self._palette)

        self._update_icon()
        self._update_name()
        self._update_state()

        # Update badge
        caps = model.props.capabilities
        if model.get_nm_network().is_favorite():
            self.props.badge_name = "badge-star"
        elif (caps & NM_802_11_CAP_PROTO_WEP) or (caps & NM_802_11_CAP_PROTO_WPA) or (caps & NM_802_11_CAP_PROTO_WPA2):
            self.props.badge_name = "badge-locked"

    def _create_palette(self):
        p = palette.Palette(self._model.props.name, menu_after_content=True)
        if not self._meshdev:
            return p

        # Only show disconnect when there's a mesh device, because mesh takes
        # priority over the normal wireless device.  NM doesn't have a "disconnect"
        # method for a device either (for various reasons) so this doesn't
        # have a good mapping 
        self._disconnect_item = gtk.MenuItem(_('Disconnect...'))
        self._disconnect_item.connect('activate', self._disconnect_activate_cb)
        p.menu.append(self._disconnect_item)
        if self._model.props.state == accesspointmodel.STATE_CONNECTED:
            self._disconnect_item.show()
        return p

    def _disconnect_activate_cb(self, menuitem):
        # Disconnection for an AP means activating the default mesh device
        network_manager = hardwaremanager.get_network_manager()
        if network_manager and self._meshdev:
            network_manager.set_active_device(self._meshdev)

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()

    def _name_changed_cb(self, model, pspec):
        self._update_name()

    def _state_changed_cb(self, model, pspec):
        self._update_state()

    def _activate_cb(self, icon):
        network_manager = hardwaremanager.get_network_manager()
        if network_manager:
            device = self._model.get_nm_device()
            network = self._model.get_nm_network()
            network_manager.set_active_device(device, network)

    def _update_name(self):
        self._palette.set_primary_text(self._model.props.name)

    def _update_icon(self):
        icon_name = get_icon_state(_ICON_NAME, self._model.props.strength)
        if icon_name:
            self.props.icon_name = icon_name        

    def _update_state(self):
        if self._model.props.state == accesspointmodel.STATE_CONNECTING:
            if self._disconnect_item:
                self._disconnect_item.hide()
            self.props.pulse_time = 1.0
            self.props.colors = [
                [ style.Color(self._device_stroke).get_svg(),
                  style.Color(self._device_fill).get_svg() ],
                [ style.Color(self._device_stroke).get_svg(),
                  '#e2e2e2' ]
            ]
        elif self._model.props.state == accesspointmodel.STATE_CONNECTED:
            if self._disconnect_item:
                self._disconnect_item.show()
            self.props.pulse_time = 0.0
            self.props.colors = [
                [ '#ffffff',
                  style.Color(self._device_fill).get_svg() ],
                [ '#ffffff',
                  style.Color(self._device_fill).get_svg() ]
            ]
        elif self._model.props.state == accesspointmodel.STATE_NOTCONNECTED:
            if self._disconnect_item:
                self._disconnect_item.hide()
            self.props.pulse_time = 0.0
            self.props.colors = [
                [ style.Color(self._device_stroke).get_svg(),
                  style.Color(self._device_fill).get_svg() ]
            ]


_MESH_ICON_NAME = 'network-mesh'

class MeshDeviceView(PulsingIcon):
    def __init__(self, nm_device, channel):
        if not channel in [1, 6, 11]:
            raise ValueError("Invalid channel %d" % channel)

        PulsingIcon.__init__(self, size=style.STANDARD_ICON_SIZE,
                             icon_name=_MESH_ICON_NAME, cache=True)

        self._nm_device = nm_device
        self.channel = channel
        self.props.badge_name = "badge-channel-%d" % self.channel

        self._disconnect_item = None
        self._palette = self._create_palette()
        self.set_palette(self._palette)

        mycolor = profile.get_color()
        self._device_fill = mycolor.get_fill_color()
        self._device_stroke = mycolor.get_stroke_color()

        self.connect('activated', self._activate_cb)

        self._nm_device.connect('state-changed', self._state_changed_cb)
        self._nm_device.connect('activation-stage-changed', self._state_changed_cb)
        self._update_state()

    def _create_palette(self):
        p = palette.Palette(_("Mesh Network") + " " + str(self.channel), menu_after_content=True)

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
            self.props.pulse_time = 0.75
            self.props.colors = [
                [ style.Color(self._device_stroke).get_svg(),
                    style.Color(self._device_fill).get_svg() ],
                [ style.Color(self._device_stroke).get_svg(),
                    '#e2e2e2' ]
            ]
        elif state == nmclient.DEVICE_STATE_ACTIVATED and chan == self.channel:
            self._disconnect_item.show()
            self.props.pulse_time = 0.0
            self.props.colors = [
                [ '#ffffff',
                    style.Color(self._device_fill).get_svg() ],
                [ '#ffffff',
                    style.Color(self._device_fill).get_svg() ]
            ]
        elif state == nmclient.DEVICE_STATE_INACTIVE or chan != self.channel:
            self._disconnect_item.hide()
            self.props.pulse_time = 0.0
            self.props.colors = [
                [ style.Color(self._device_stroke).get_svg(),
                  style.Color(self._device_fill).get_svg() ]
            ]
        else:
            raise RuntimeError("Shouldn't get here")

class ActivityView(hippo.CanvasBox):
    def __init__(self, shell, model):
        hippo.CanvasBox.__init__(self)

        self._shell = shell
        self._model = model
        self._icons = {}

        self._layout = SnowflakeLayout()
        self.set_layout(self._layout)

        self._icon = CanvasIcon(file_name=model.get_icon_name(),
                                xo_color=model.get_color(), cache=True,
                                size=style.STANDARD_ICON_SIZE)
        self._icon.connect('activated', self._clicked_cb)
        self._icon.set_tooltip(self._model.activity.props.name)
        self._layout.add_center(self._icon)

        self._model.activity.connect('notify::name', self._name_changed_cb)

    def _name_changed_cb(self, activity, pspec):
        self._icon.set_tooltip(activity.props.name)

    def has_buddy_icon(self, key):
        return self._icons.has_key(key)

    def add_buddy_icon(self, key, icon):
        self._icons[key] = icon
        self._layout.add(icon)

    def remove_buddy_icon(self, key):
        icon = self._icons[key]
        self.remove(icon)
        del self._icons[key]

    def _clicked_cb(self, item):
        bundle_id = self._model.get_bundle_id()
        self._shell.join_activity(bundle_id, self._model.get_id())

class MeshBox(hippo.CanvasBox):
    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff)

        self._shell = shell
        self._model = shell.get_model().get_mesh()
        self._buddies = {}
        self._activities = {}
        self._access_points = {}
        self._mesh = {}
        self._buddy_to_activity = {}
        self._suspended = True

        self._layout = SpreadLayout()
        self.set_layout(self._layout)

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
            self._mesh_added_cb(self._model, self._model.get_mesh())

        self._model.connect('mesh-added',
                            self._mesh_added_cb)
        self._model.connect('mesh-removed',
                            self._mesh_removed_cb)

    def _mesh_added_cb(self, model, meshdev):
        self._add_mesh_icon(meshdev, 1)
        self._add_mesh_icon(meshdev, 6)
        self._add_mesh_icon(meshdev, 11)

    def _mesh_removed_cb(self, model):
        self._remove_mesh_icon(1)
        self._remove_mesh_icon(6)
        self._remove_mesh_icon(11)

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
        icon = BuddyIcon(self._shell, buddy_model)
        if buddy_model.is_owner():
            self._layout.add_center(icon)
        else:
            self._layout.add(icon)

        self._buddies[buddy_model.get_key()] = icon

    def _remove_alone_buddy(self, buddy_model):
        icon = self._buddies[buddy_model.get_key()]
        self._layout.remove(icon)
        del self._buddies[buddy_model.get_key()]

    def _remove_buddy(self, buddy_model):
        key = buddy_model.get_key()
        if self._buddies.has_key(key):
            self._remove_alone_buddy(buddy_model)
        else:
            for activity in self._activities.values():
                if activity.has_buddy_icon(key):
                    activity.remove_buddy_icon(key)

    def _move_buddy(self, buddy_model, activity_model):
        key = buddy_model.get_key()

        self._remove_buddy(buddy_model)

        if activity_model == None:
            self._add_alone_buddy(buddy_model)
        else:
            activity = self._activities[activity_model.get_id()]

            icon = BuddyIcon(self._shell, buddy_model,
                             style.SMALL_ICON_SIZE)
            activity.add_buddy_icon(buddy_model.get_key(), icon)

    def _add_activity(self, activity_model):
        icon = ActivityView(self._shell, activity_model)
        self._layout.add(icon)

        self._activities[activity_model.get_id()] = icon

    def _remove_activity(self, activity_model):
        icon = self._activities[activity_model.get_id()]
        self._layout.remove(icon)
        del self._activities[activity_model.get_id()]

    def _add_access_point(self, ap_model):
        meshdev = self._model.get_mesh()
        icon = AccessPointView(ap_model, meshdev)
        self._layout.add(icon)

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
