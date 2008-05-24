# Copyright (C) 2007, Red Hat, Inc.
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

from sugar.graphics.icon import CanvasIcon
from sugar.graphics import style
from sugar.graphics.xocolor import XoColor

class ColorPicker(hippo.CanvasBox, hippo.CanvasItem):
    def __init__(self, **kwargs):
        hippo.CanvasBox.__init__(self, **kwargs)
        self.props.orientation = hippo.ORIENTATION_HORIZONTAL
        self._xo_color = None

        self._xo = CanvasIcon(size=style.XLARGE_ICON_SIZE,
                              icon_name='computer-xo')
        self._set_random_colors()
        self._xo.connect('activated', self._xo_activated_cb)
        self.append(self._xo)

    def _xo_activated_cb(self, item):
        self._set_random_colors()

    def get_color(self):
        return self._xo_color

    def _set_random_colors(self):
        self._xo_color = XoColor()
        self._xo.props.xo_color = self._xo_color
