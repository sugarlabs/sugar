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

import os
import signal
import math
from gettext import gettext as _

import gobject
import gtk
import hippo
import dbus

from hardware import hardwaremanager
from sugar.graphics import style
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import Palette, CanvasInvoker
from sugar.graphics.icon import CanvasIcon
from sugar import profile
from sugar import env

from view.home.activitiesdonut import ActivitiesDonut
from view.devices import deviceview
from view.home.MyIcon import MyIcon
from model.shellmodel import ShellModel

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff)

        self._redraw_id = None

        shell_model = shell.get_model()

        top_box = hippo.CanvasBox(yalign=hippo.ALIGNMENT_START,
                                  box_height=style.GRID_CELL_SIZE,
                                  orientation=hippo.ORIENTATION_HORIZONTAL)
        self.append(top_box, hippo.PACK_EXPAND)

        nw_arrow = CanvasIcon(icon_name='arrow_NW',
                              xalign=hippo.ALIGNMENT_START)
        top_box.append(nw_arrow)

        arrows_separator = hippo.CanvasBox()
        top_box.append(arrows_separator, hippo.PACK_EXPAND)

        ne_arrow = CanvasIcon(icon_name='arrow_NE',
                              xalign=hippo.ALIGNMENT_END)
        top_box.append(ne_arrow)

        self._donut = ActivitiesDonut(shell)
        self.append(self._donut)

        bottom_box = hippo.CanvasBox(yalign=hippo.ALIGNMENT_END,
                                     box_height=style.GRID_CELL_SIZE,
                                     orientation=hippo.ORIENTATION_HORIZONTAL)
        self.append(bottom_box, hippo.PACK_EXPAND)

        self._my_icon = _MyIcon(shell, style.XLARGE_ICON_SIZE)
        self.append(self._my_icon, hippo.PACK_FIXED)

        sw_arrow = CanvasIcon(icon_name='arrow_SW',
                              xalign=hippo.ALIGNMENT_START)
        bottom_box.append(sw_arrow)

        devices_box = _DevicesBox(shell_model.get_devices())
        bottom_box.append(devices_box, hippo.PACK_EXPAND)

        se_arrow = CanvasIcon(icon_name='arrow_SE',
                              xalign=hippo.ALIGNMENT_END)
        bottom_box.append(se_arrow)

        self._arrows = [ nw_arrow, ne_arrow, sw_arrow, se_arrow ]

        shell_model.connect('notify::state',
                            self._shell_state_changed_cb)
        shell_model.connect('notify::zoom-level',
                            self._shell_zoom_level_changed_cb)

    def _shell_zoom_level_changed_cb(self, model, pspec):
        for arrow in self._arrows:
            arrow.destroy()
        self._arrows = []

    def _shell_state_changed_cb(self, model, pspec):
        # FIXME implement this
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            pass

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [icon_width, icon_height] = self._my_icon.get_allocation()
        self.set_position(self._my_icon, (width - icon_width) / 2,
                          (height - icon_height) / 2)
                  
    _REDRAW_TIMEOUT = 5 * 60 * 1000 # 5 minutes

    def resume(self):
        if self._redraw_id is None:
            self._redraw_id = gobject.timeout_add(self._REDRAW_TIMEOUT,
                                                  self._redraw_activity_ring)
            self._redraw_activity_ring()

    def suspend(self):
        if self._redraw_id is not None:
            gobject.source_remove(self._redraw_id)
            self._redraw_id = None

    def _redraw_activity_ring(self):
        self._donut.redraw()
        return True

    def has_activities(self):
        return self._donut.has_activities()

    def enable_xo_palette(self):
        self._my_icon.enable_palette()

    def grab_and_rotate(self):
        pass
            
    def rotate(self):
        pass

    def release(self):
        pass

class _DevicesBox(hippo.CanvasBox):
    def __init__(self, devices_model):
        gobject.GObject.__init__(self,
                orientation=hippo.ORIENTATION_HORIZONTAL,
                xalign=hippo.ALIGNMENT_CENTER)

        self._device_icons = {}

        for device in devices_model:
            self._add_device(device)

        devices_model.connect('device-appeared',
                              self._device_appeared_cb)
        devices_model.connect('device-disappeared',
                              self._device_disappeared_cb)

    def _add_device(self, device):
        view = deviceview.create(device)
        self.append(view)
        self._device_icons[device.get_id()] = view

    def _remove_device(self, device):
        self.remove(self._device_icons[device.get_id()])
        del self._device_icons[device.get_id()]

    def _device_appeared_cb(self, model, device):
        self._add_device(device)

    def _device_disappeared_cb(self, model, device):
        self._remove_device(device)

class _MyIcon(MyIcon):
    def __init__(self, shell, scale):
        MyIcon.__init__(self, scale)

        self._power_manager = None
        self._shell = shell

    def enable_palette(self):
        palette = Palette(profile.get_nick_name())

        reboot_menu_item = gtk.MenuItem(_('Reboot'))
        reboot_menu_item.connect('activate', self._reboot_activate_cb)
        shutdown_menu_item = gtk.MenuItem(_('Shutdown'))
        shutdown_menu_item.connect('activate', self._shutdown_activate_cb)
        
        palette.menu.append(reboot_menu_item)
        palette.menu.append(shutdown_menu_item)
        reboot_menu_item.show()
        shutdown_menu_item.show()

        self.set_palette(palette)

    def _reboot_activate_cb(self, menuitem):
        model = self._shell.get_model()
        model.props.state = ShellModel.STATE_SHUTDOWN

        pm = self._get_power_manager()

        hw_manager = hardwaremanager.get_manager()
        hw_manager.shutdown()

        if env.is_emulator():
            self._close_emulator()
        else:
            pm.Reboot()

    def _shutdown_activate_cb(self, menuitem):
        model = self._shell.get_model()
        model.props.state = ShellModel.STATE_SHUTDOWN

        pm = self._get_power_manager()

        hw_manager = hardwaremanager.get_manager()
        hw_manager.shutdown()

        if env.is_emulator():
            self._close_emulator()
        else:
            pm.Shutdown()

    def _close_emulator(self):
        if os.environ.has_key('SUGAR_EMULATOR_PID'):
            pid = int(os.environ['SUGAR_EMULATOR_PID'])
            os.kill(pid, signal.SIGTERM)

    def _get_power_manager(self):
        if self._power_manager is None:
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.Hal', 
                                '/org/freedesktop/Hal/devices/computer')
            self._power_manager = dbus.Interface(proxy, \
                            'org.freedesktop.Hal.Device.SystemPowerManagement') 

        return self._power_manager
