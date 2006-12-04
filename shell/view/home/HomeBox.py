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
from sugar.graphics.grid import Grid
from sugar.graphics import style

class HomeBox(hippo.CanvasBox, hippo.CanvasItem):
    __gtype_name__ = 'SugarHomeBox'

    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, background_color=0xe2e2e2ff,
                                 yalign=2)

        grid = Grid()
        donut = ActivitiesDonut(shell, box_width=grid.dimension(7),
                                box_height=grid.dimension(7))
        self.append(donut)

        self._my_icon = MyIcon()
        style.apply_stylesheet(self._my_icon, 'home.MyIcon')
        self.append(self._my_icon, hippo.PACK_FIXED)

    def do_allocate(self, width, height):
        hippo.CanvasBox.do_allocate(self, width, height)

        [icon_width, icon_height] = self._my_icon.get_allocation()
        self.move(self._my_icon, (width - icon_width) / 2,
                  (height - icon_height) / 2)
