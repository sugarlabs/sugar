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

import logging
from gettext import gettext as _

import gobject
import gtk

from sugar.graphics.icon import get_icon_state
from sugar.graphics.tray import TrayIcon
from sugar.graphics import style
from sugar.graphics.palette import Palette
from sugar import profile

from jarabe.model import network
from jarabe.frame.frameinvoker import FrameWidgetInvoker

_ICON_NAME = 'network-wireless'

STATE_ACTIVATING = 0
STATE_ACTIVATED  = 1
STATE_INACTIVE   = 2

nm_state_to_state = {
    network.DEVICE_STATE_ACTIVATING : STATE_ACTIVATING,
    network.DEVICE_STATE_ACTIVATED  : STATE_ACTIVATED,
    network.DEVICE_STATE_INACTIVE   : STATE_INACTIVE
}

class WirelessDeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 300

    def __init__(self, nm_device):
        TrayIcon.__init__(self, icon_name=_ICON_NAME)

        self.model = WirelessDeviceModel(nm_device)

        meshdev = None
        network_manager = network.get_manager()
        for dev in network_manager.get_devices():
            if dev.get_type() == network.DEVICE_TYPE_802_11_MESH_OLPC:
                meshdev = dev
                break

        self._counter = 0
        self.palette = WirelessPalette(self._get_palette_primary_text(),
                                       meshdev)
        self.set_palette(self.palette)
        self.palette.props.invoker = FrameWidgetInvoker(self)
        self.palette.set_group_id('frame')
        self.palette.set_frequency(self._model.props.frequency)

        self._model.connect('notify::name', self._name_changed_cb)
        self._model.connect('notify::strength', self._strength_changed_cb)
        self._model.connect('notify::state', self._state_changed_cb)

        self._update_icon()
        self._update_state()

    def _get_palette_primary_text(self):
        if self._model.props.state == STATE_INACTIVE:
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
        self._update_icon()
        self._update_state()
        self.palette.set_primary_text(self._get_palette_primary_text())

    def _update_icon(self):
        # keep this code in sync with view/home/MeshBox.py
        strength = self._model.props.strength
        if self._model.props.state == STATE_INACTIVE:
            strength = 0
        if self._model.props.state == STATE_ACTIVATED:
            icon_name = '%s-connected' % _ICON_NAME
        else:
            icon_name = _ICON_NAME
        icon_name = get_icon_state(icon_name, strength)
        if icon_name:
            self.icon.props.icon_name = icon_name

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        if state == STATE_ACTIVATING:
            self.icon.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.icon.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
        elif state == STATE_ACTIVATED:
            (stroke, fill) = self._model.get_active_network_colors()
            self.icon.props.stroke_color = stroke
            self.icon.props.fill_color = fill
        elif state == STATE_INACTIVE:
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
        network_manager = network.get_manager()
        if network_manager and self._meshdev:
            network_manager.set_active_device(self._meshdev)

    def set_frequency(self, freq):
        try:
            chan = network.freq_to_channel(freq)
        except KeyError:
            chan = 0
        self._chan_label.set_text("%s: %d" % (_("Channel"), chan))

class MeshDeviceView(TrayIcon):

    FRAME_POSITION_RELATIVE = 400

    def __init__(self, nm_device):
        TrayIcon.__init__(self, icon_name='network-mesh')

        self.model = MeshDeviceModel(nm_device)

        self.palette = MeshPalette(_("Mesh Network"), self.model)
        self.set_palette(self.palette)
        self.palette.props.invoker = FrameWidgetInvoker(self)
        self.palette.set_group_id('frame')

        self.model.connect('notify::state', self._state_changed_cb)
        self.model.connect('notify::activation-stage', self._state_changed_cb)
        self._update_state()

    def _state_changed_cb(self, model, pspec):
        self._update_state()

    def _update_state(self):
        # FIXME Change icon colors once we have real icons
        state = self._model.props.state
        self.palette.update_state(state)

        if state == STATE_ACTIVATING:
            self.icon.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.icon.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()
        elif state == STATE_ACTIVATED:
            self.icon.props.xo_color = profile.get_color()
        elif state == STATE_INACTIVE:
            self.icon.props.fill_color = style.COLOR_INACTIVE_FILL.get_svg()
            self.icon.props.stroke_color = style.COLOR_INACTIVE_STROKE.get_svg()

        if state == STATE_INACTIVE:
            self.palette.set_primary_text(_("Mesh Network"))
        else:
            chan = network.freq_to_channel(self._model.props.frequency)
            if chan > 0:
                self.palette.set_primary_text(_("Mesh Network") + " %d" % chan)
            self.palette.set_mesh_step(self._model.props.mesh_step, state)

class MeshPalette(Palette):
    def __init__(self, primary_text, model):
        Palette.__init__(self, primary_text, menu_after_content=True)
        self._model = model

        self._step_label = gtk.Label()
        self._step_label.show()

        vbox = gtk.VBox()
        vbox.pack_start(self._step_label)
        vbox.show()

        self.set_content(vbox)

        self._disconnect_item = gtk.MenuItem(_('Disconnect...'))
        self._disconnect_item.connect('activate', self._disconnect_activate_cb)
        self.menu.append(self._disconnect_item)

    def update_state(self, state):
        if state == STATE_ACTIVATED:
            self._disconnect_item.show()
        else:
            self._disconnect_item.hide()

    def _disconnect_activate_cb(self, menuitem):
        # Disconnection for an mesh means activating the default mesh device
        # again without a channel
        network_manager = network.get_manager()
        nm_device = self._model.get_nm_device()
        if network_manager and nm_device:
            network_manager.set_active_device(nm_device)

    def set_mesh_step(self, step, state):
        label = ""
        if step == 1:
            if state == STATE_ACTIVATED:
                label = _("Connected to a School Mesh Portal")
            elif state == STATE_ACTIVATING:
                label = _("Looking for a School Mesh Portal...")
        elif step == 3:
            if state == STATE_ACTIVATED:
                label = _("Connected to an XO Mesh Portal")
            elif state == STATE_ACTIVATING:
                label = _("Looking for an XO Mesh Portal...")
        elif step == 4:
            if state == STATE_ACTIVATED:
                label = _("Connected to a Simple Mesh")
            elif state == STATE_ACTIVATING:
                label = _("Starting a Simple Mesh")

        if len(label):
            self._step_label.set_text(label)
        else:
            logging.debug("Unhandled mesh step %d" % step)
            self._step_label.set_text(_("Unknown Mesh"))

class WirelessDeviceModel(gobject.GObject):
    __gproperties__ = {
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE),
        'state'    : (int, None, None, STATE_ACTIVATING,
                      STATE_INACTIVE, 0, gobject.PARAM_READABLE),
        'activation-stage': (int, None, None, 0, 7, 0, gobject.PARAM_READABLE),
        'frequency': (float, None, None, 0, 2.72, 0, gobject.PARAM_READABLE),
        'mesh-step': (int, None, None, 0, 4, 0, gobject.PARAM_READABLE),
    }

    def __init__(self, nm_device):
        gobject.GObject.__init__(self)

        self._nm_device = nm_device

        self._nm_device.connect('strength-changed',
                                self._strength_changed_cb)
        self._nm_device.connect('state-changed',
                                self._state_changed_cb)
        self._nm_device.connect('activation-stage-changed',
                                self._activation_stage_changed_cb)

    def _strength_changed_cb(self, nm_device):
        self.notify('strength')

    def _state_changed_cb(self, nm_device):
        self.notify('state')

    def _activation_stage_changed_cb(self, nm_device):
        self.notify('activation-stage')

    def do_get_property(self, pspec):
        if pspec.name == 'strength':
            return self._nm_device.get_strength()
        elif pspec.name == 'state':
            nm_state = self._nm_device.get_state()
            return nm_state_to_state[nm_state]
        elif pspec.name == 'activation-stage':
            return self._nm_device.get_activation_stage()
        elif pspec.name == 'frequency':
            return self._nm_device.get_frequency()
        elif pspec.name == 'mesh-step':
            return self._nm_device.get_mesh_step()

    def get_type(self):
        return 'mesh'

    def get_id(self):
        return str(self._nm_device.get_op())

    def get_nm_device(self):
        return self._nm_device

class MeshDeviceModel(gobject.GObject):
    __gproperties__ = {
        'name'     : (str, None, None, None,
                      gobject.PARAM_READABLE),
        'strength' : (int, None, None, 0, 100, 0,
                      gobject.PARAM_READABLE),
        'state'    : (int, None, None, STATE_ACTIVATING,
                      STATE_INACTIVE, 0, gobject.PARAM_READABLE),
        'frequency': (float, None, None, 0.0, 9999.99, 0.0,
                      gobject.PARAM_READABLE)
    }

    def __init__(self, nm_device):
        gobject.GObject.__init__(self)

        self._nm_device = nm_device

        self._nm_device.connect('strength-changed',
                                self._strength_changed_cb)
        self._nm_device.connect('ssid-changed',
                                self._ssid_changed_cb)
        self._nm_device.connect('state-changed',
                                self._state_changed_cb)

    def _strength_changed_cb(self, nm_device):
        self.notify('strength')

    def _ssid_changed_cb(self, nm_device):
        self.notify('name')

    def _state_changed_cb(self, nm_device):
        self.notify('state')

    def do_get_property(self, pspec):
        if pspec.name == 'strength':
            return self._nm_device.get_strength()
        elif pspec.name == 'name':
            logging.debug('wireless.Device.props.name: %s' %
                    self._nm_device.get_ssid())
            return self._nm_device.get_ssid()
        elif pspec.name == 'state':
            nm_state = self._nm_device.get_state()
            return nm_state_to_state[nm_state]
        elif pspec.name == 'frequency':
            return self._nm_device.get_frequency()

    def get_type(self):
        return 'wireless'

    def get_id(self):
        return str(self._nm_device.get_op())

    def get_active_network_colors(self):
        net = self._nm_device.get_active_network()
        if not net:
            return (None, None)
        return net.get_colors()

_devices = {}
_sigids = {}

def setup(tray):
    network_manager = network.get_manager()
    if not network_manager:
        return

    for dev in network_manager.get_devices():
        _check_network_device(dev)

    network_manager.connect('device-added',
                            _network_device_added_cb, tray)
    network_manager.connect('device-activating',
                            _network_device_activating_cb, tray)
    network_manager.connect('device-removed',
                            _network_device_removed_cb, tray)

def _network_device_added_cb(manager, nm_device, tray):
    state = nm_device.get_state()
    if state == network.DEVICE_STATE_ACTIVATING or \
        state == network.DEVICE_STATE_ACTIVATED:
        _check_network_device(tray, nm_device)

def _network_device_activating_cb(manager, nm_device, tray):
    _check_network_device(tray, nm_device)

def _network_device_removed_cb(manager, nm_device, tray):
    if _devices.has_key(str(nm_device.get_op())):
        tray.remove_device(_devices[str(nm_device.get_op())])

def _check_network_device(tray, nm_device):
    if not nm_device.is_valid():
        logging.debug("Device %s not valid" % nm_device.get_op())
        return

    dtype = nm_device.get_type()
    if dtype == network.DEVICE_TYPE_802_11_WIRELESS \
        or dtype == network.DEVICE_TYPE_802_11_MESH_OLPC:
        _add_network_device(tray, nm_device)

def _network_device_state_changed_cb(model, param, tray, dev):
    if dev.props.state == STATE_INACTIVE:
        tray.remove_device(dev)

def _add_network_device(tray, nm_device):
    if _devices.has_key(str(nm_device.get_op())):
        logging.debug("Tried to add device %s twice" % nm_device.get_op())
        return

    dtype = nm_device.get_type()
    if dtype == network.DEVICE_TYPE_802_11_WIRELESS:
        dev = WirelessDeviceView(nm_device)
        tray.add_device(dev)
        sigid = dev.model.connect('notify::state',
                                  _network_device_state_changed_cb, tray, dev)
        _sigids[dev] = sigid
    if dtype == network.DEVICE_TYPE_802_11_MESH_OLPC:
        dev = MeshDeviceView(nm_device)
        tray.add_device(dev)
        sigid = dev.model.connect('notify::state',
                                  _network_device_state_changed_cb, tray, dev)
        _sigids[dev] = sigid
