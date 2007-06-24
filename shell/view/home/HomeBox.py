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

import math
from gettext import gettext as _

import gobject
import gtk
import hippo

from sugar.graphics import units
from sugar.graphics import color
from sugar.graphics.xocolor import XoColor
from sugar.graphics.palette import Palette, CanvasInvoker
from sugar import profile

from view.home.activitiesdonut import ActivitiesDonut
from view.devices import deviceview
from view.home.MyIcon import MyIcon
from model.ShellModel import ShellModel

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff, yalign=2)

        self._donut = ActivitiesDonut(shell,
                                      box_width=units.grid_to_pixels(6),
                                      box_height=units.grid_to_pixels(6))
        self.append(self._donut)

        self._my_icon = HomeMyIcon(units.XLARGE_ICON_SCALE)
        self.append(self._my_icon, hippo.PACK_FIXED)

        shell_model = shell.get_model()
        shell_model.connect('notify::state',
                            self._shell_state_changed_cb)

        self._device_icons = {}

        devices_model = shell_model.get_devices()
        for device in devices_model:
            self._add_device(device)

        devices_model.connect('device-appeared',
                              self._device_appeared_cb)
        devices_model.connect('device-disappeared',
                              self._device_disappeared_cb)

    def _add_device(self, device):
        view = deviceview.create(device)
        self.append(view, hippo.PACK_FIXED)
        self._device_icons[device.get_id()] = view

    def _remove_device(self, device):
        self.remove(self._device_icons[device.get_id()])
        del self._device_icons[device.get_id()]

    def _device_appeared_cb(self, model, device):
        self._add_device(device)

    def _device_disappeared_cb(self, model, device):
        self._remove_device(device)

    def _shell_state_changed_cb(self, model, pspec):
        # FIXME handle all possible mode switches
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            if self._donut:
                self.remove(self._donut)
                self._donut = None
                self._my_icon.props.stroke_color = color.BUTTON_INACTIVE
                self._my_icon.props.fill_color = \
                        color.BUTTON_INACTIVE_BACKGROUND
                self._my_icon.props.background_color = \
                        color.BUTTON_INACTIVE_BACKGROUND

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [icon_width, icon_height] = self._my_icon.get_allocation()
        self.set_position(self._my_icon, (width - icon_width) / 2,
                          (height - icon_height) / 2)

        i = 0
        for icon in self._device_icons.values():
            angle = 2 * math.pi / len(self._device_icons) * i + math.pi / 2
            radius = units.grid_to_pixels(4)

            [icon_width, icon_height] = icon.get_allocation()

            x = int(radius * math.cos(angle)) - icon_width / 2
            y = int(radius * math.sin(angle)) - icon_height / 2
            self.set_position(icon, x + width / 2, y + height / 2)            

            i += 1
                  
    def has_activities(self):
        return self._donut.has_activities()

    def grab_and_rotate(self):
        pass
            
    def rotate(self):
        pass

    def release(self):
        pass

# TODO: Most or all of it should move to CanvasIcon.
class HomeMyIcon(MyIcon):
    _POPUP_PALETTE_DELAY = 100

    def __init__(self, scale):
        MyIcon.__init__(self, scale)

        self._palette = Palette()
        self._palette.set_primary_state(profile.get_nick_name())
        self._palette.props.invoker = CanvasInvoker(self)
        
        shutdown_menu_item = gtk.MenuItem(_('Shutdown'))
        shutdown_menu_item.connect('activate', self._shutdown_activate_cb)
        self._palette.append_menu_item(shutdown_menu_item)
        
        self.connect('motion-notify-event',self._motion_notify_event_cb)
        self._enter_tag = None
        self._leave_tag = None

    def _motion_notify_event_cb(self, button, event):
        if event.detail == hippo.MOTION_DETAIL_ENTER:
            gtk.gdk.pointer_ungrab()

            if self._leave_tag:
                gobject.source_remove(self._leave_tag)
                self._leave_tag = None

            self._enter_tag = gobject.timeout_add(self._POPUP_PALETTE_DELAY, \
                self._show_palette)
        elif event.detail == hippo.MOTION_DETAIL_LEAVE:
            if self._enter_tag:
                gobject.source_remove(self._enter_tag)
                self._enter_tag = None

            self._leave_tag = gobject.timeout_add(self._POPUP_PALETTE_DELAY,\
                self._hide_palette)

        return False

    def _show_palette(self):
        self._palette.popup()
        return False

    def _hide_palette(self):
        # Just hide the palette if the mouse pointer is 
        # out of the toolbutton and the palette
        if self._is_mouse_out(self._palette):
            self._palette.popdown()
        else:
            gtk.gdk.pointer_ungrab()
        
        return False

    def _pointer_grab(self):
        gtk.gdk.pointer_grab(self.window, owner_events=True,\
            event_mask=gtk.gdk.PROPERTY_CHANGE_MASK )

    def _is_mouse_out(self, widget):
        mouse_x, mouse_y = widget.get_pointer()
        event_rect = gtk.gdk.Rectangle(mouse_x, mouse_y, 1, 1)

        if widget.allocation.intersect(event_rect).width == 0:
            return True
        else:
            return False

    def _shutdown_activate_cb(self, menuitem):
        pass

