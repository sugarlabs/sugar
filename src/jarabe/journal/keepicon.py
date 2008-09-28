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

import gobject
import hippo

from sugar.graphics.icon import CanvasIcon
from sugar.graphics import style
from sugar import profile

class KeepIcon(CanvasIcon):
    def __init__(self, keep):
        CanvasIcon.__init__(self, icon_name='emblem-favorite',
                            box_width=style.GRID_CELL_SIZE * 3 / 5,
                            size=style.SMALL_ICON_SIZE)
        self.connect('motion-notify-event', self.__motion_notify_event_cb)

        self._keep = None
        self.set_keep(keep)

    def set_keep(self, keep):
        if keep == self._keep:
            return

        self._keep = keep
        if keep:
            self.props.xo_color = profile.get_color()
        else:
            self.props.stroke_color = style.COLOR_BUTTON_GREY.get_svg()
            self.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

    def get_keep(self):
        return self._keep

    keep = gobject.property(type=int, default=0, getter=get_keep,
                            setter=set_keep)

    def __motion_notify_event_cb(self, icon, event):
        if not self._keep:
            if event.detail == hippo.MOTION_DETAIL_ENTER:
                icon.props.fill_color = style.COLOR_BUTTON_GREY.get_svg()
            elif event.detail == hippo.MOTION_DETAIL_LEAVE:
                icon.props.fill_color = style.COLOR_TRANSPARENT.get_svg()

