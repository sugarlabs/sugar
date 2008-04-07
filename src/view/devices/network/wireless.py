#
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

import gtk

from sugar.graphics.icon import get_icon_state
from sugar.graphics.tray import TrayIcon
from sugar.graphics import style
from sugar.graphics.palette import Palette

from model.devices.network import wireless
from model.devices import device
from hardware import hardwaremanager
from hardware import nmclient
from view.frame.frameinvoker import FrameWidgetInvoker

_ICON_NAME = 'network-wireless'

class DeviceView(TrayIcon):
    def __init__(self, model):
        TrayIcon.__init__(self, icon_name=_ICON_NAME)
        self._model = model

        meshdev = None
        network_manager = hardwaremanager.get_network_manager()
        for device in network_manager.get_devices():
            if device.get_type() == nmclient.DEVICE_TYPE_802_11_MESH_OLPC:
                meshdev = device
                break

        self._counter = 0
        self.palette = WirelessPalette(self._get_palette_primary_text(), meshdev)
        self.set_palette(self.palette)
        self.palette.props.invoker = FrameWidgetInvoker(self)
        self.palette.set_group_id('frame')
        self.palette.set_frequency(self._model.props.frequency)

        model.connect('notify::name', self._name_changed_cb)
        model.connect('notify::strength', self._strength_changed_cb)
        model.connect('notify::state', self._state_changed_cb)

        self._update_icon()
        self._update_state()

    def _get_palette_primary_text(self):
        if self._model.props.state == device.STATE_INACTIVE:
            return _("Disconnected")
        return self._model.props.name

    def _strength_changed_cb(self, model, pspec):
        self._update_icon()
        # Only update frequency periodically
        if self._counter % 4 == 0:
            self.palette.set_frequency(self._model.props.frequency)
        self._counter += 1

    def _name_changed_cb(self, model, pspec):
        self.palette.set_primary_text(self._get_palette_primary_text())

    def _state_changed_cb(self, model, pspec):
        self._update_state()
        self.palette.set_primary_text(self._get_palette_primary_text())

    def _update_icon(self):
        strength = self._model.props.strength
        if self._model.props.state == device.STATE_INACTIVE:
            strength = 0
        icon_name = get_icon_state(_ICON_NAME, strength)
        if icon_name:
            self.icon.props.icon_name = icon_name

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        if state == device.STATE_ACTIVATING:
            self.icon.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.icon.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
        elif state == device.STATE_ACTIVATED:
            (stroke, fill) = self._model.get_active_network_colors()
            self.icon.props.stroke_color = stroke
            self.icon.props.fill_color = fill
        elif state == device.STATE_INACTIVE:
            self.icon.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.icon.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()

class WirelessPalette(Palette):
    def __init__(self, primary_text, meshdev):
        Palette.__init__(self, primary_text, menu_after_content=True)
        self._meshdev = meshdev

        self._chan_label = gtk.Label()
        self._chan_label.show()

        vbox = gtk.VBox()
        vbox.pack_start(self._chan_label)
        vbox.show()

        if meshdev:
            disconnect_item = gtk.MenuItem(_('Disconnect...'))
            disconnect_item.connect('activate', self._disconnect_activate_cb)
            self.menu.append(disconnect_item)
            disconnect_item.show()

        self.set_content(vbox)

    def _disconnect_activate_cb(self, menuitem):
        # Disconnection for an AP means activating the default mesh device
        network_manager = hardwaremanager.get_network_manager()
        if network_manager and self._meshdev:
            network_manager.set_active_device(self._meshdev)

    def set_frequency(self, freq):
        try:
            chan = wireless.freq_to_channel(freq)
        except KeyError:
            chan = 0
        self._chan_label.set_text("%s: %d" % (_("Channel"), chan))

