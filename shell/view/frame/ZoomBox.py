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

import hippo

from sugar.graphics import color
from sugar.graphics.iconbutton import IconButton
import sugar

class ZoomBox(hippo.CanvasBox):
    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell

        icon = IconButton(icon_name='theme:stock-zoom-mesh',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_MESH)
        self.append(icon)

        icon = IconButton(icon_name='theme:stock-zoom-friends',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_FRIENDS)
        self.append(icon)

        icon = IconButton(icon_name='theme:stock-zoom-home',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_HOME)
        self.append(icon)

        icon = IconButton(icon_name='theme:stock-zoom-activity',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated', self._level_clicked_cb, sugar.ZOOM_ACTIVITY)
        self.append(icon)

    def _level_clicked_cb(self, item, level):
        self._shell.set_zoom_level(level)
