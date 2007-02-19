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

import hippo

from view.home.activitiesdonut import ActivitiesDonut
from view.home.MyIcon import MyIcon
from model.ShellModel import ShellModel
from sugar.graphics import style
from sugar.graphics import units
from sugar.graphics.iconcolor import IconColor

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff, yalign=2)

        self._donut = ActivitiesDonut(shell,
                                      box_width=units.grid_to_pixels(7),
                                      box_height=units.grid_to_pixels(7))
        self.append(self._donut)

        self._my_icon = MyIcon()
        style.apply_stylesheet(self._my_icon, 'home.MyIcon')
        self.append(self._my_icon, hippo.PACK_FIXED)

        shell.get_model().connect('notify::state',
                                  self._shell_state_changed_cb)

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
                  
    def has_activities(self):
        return self._donut.has_activities()

    def grab_and_rotate(self):
        pass
            
    def rotate(self):
        pass

    def release(self):
        pass
