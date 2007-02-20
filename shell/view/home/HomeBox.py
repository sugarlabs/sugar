# Copyright (C) 2006, Red Hat, Inc.
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

import hippo

from sugar.graphics import units
from sugar.graphics.iconcolor import IconColor

from view.home.activitiesdonut import ActivitiesDonut
from view.devices import deviceview
from view.home.MyIcon import MyIcon
from model.ShellModel import ShellModel

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff, yalign=2)

        self._donut = ActivitiesDonut(shell,
                                      box_width=units.grid_to_pixels(7),
                                      box_height=units.grid_to_pixels(7))
        self.append(self._donut)

        self._my_icon = MyIcon(units.XLARGE_ICON_SCALE)
        self.append(self._my_icon, hippo.PACK_FIXED)

        shell_model = shell.get_model()
        shell_model.connect('notify::state',
                            self._shell_state_changed_cb)

        self._device_icons = []
        for device in shell_model.get_devices():
            self._add_device(device)

    def _add_device(self, device):
        view = deviceview.create(device)
        self.append(view, hippo.PACK_FIXED)
        self._device_icons.append(view)

    def _shell_state_changed_cb(self, model, pspec):
        # FIXME handle all possible mode switches
        if model.props.state == ShellModel.STATE_SHUTDOWN:
            if self._donut:
                self.remove(self._donut)
                self._donut = None
                self._my_icon.props.color = IconColor('insensitive')

    def do_allocate(self, width, height, origin_changed):
        hippo.CanvasBox.do_allocate(self, width, height, origin_changed)

        [icon_width, icon_height] = self._my_icon.get_allocation()
        self.set_position(self._my_icon, (width - icon_width) / 2,
                          (height - icon_height) / 2)

        i = 0
        for icon in self._device_icons:
            angle = 2 * math.pi / len(self._device_icons) * i + math.pi / 2
            radius = units.grid_to_pixels(5)

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
