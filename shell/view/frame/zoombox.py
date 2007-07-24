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

import hippo

from sugar.graphics import color
from sugar.graphics.palette import Palette
from sugar.graphics.iconbutton import IconButton
from frameinvoker import FrameCanvasInvoker

from model.shellmodel import ShellModel

class ZoomBox(hippo.CanvasBox):
    def __init__(self, shell):
        hippo.CanvasBox.__init__(self, orientation=hippo.ORIENTATION_HORIZONTAL)

        self._shell = shell

        icon = IconButton(icon_name='theme:zoom-mesh',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated',
                     self._level_clicked_cb,
                     ShellModel.ZOOM_MESH)
        self.append(icon)

        palette = Palette(_('Neighborhood'))
        palette.props.invoker = FrameCanvasInvoker(icon)
        palette.set_group_id('frame')
        icon.set_palette(palette)

        icon = IconButton(icon_name='theme:zoom-friends',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated',
                     self._level_clicked_cb,
                     ShellModel.ZOOM_FRIENDS)
        self.append(icon)

        palette = Palette(_('Group'))
        palette.props.invoker = FrameCanvasInvoker(icon)
        palette.set_group_id('frame')
        icon.set_palette(palette)

        icon = IconButton(icon_name='theme:zoom-home',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated',
                     self._level_clicked_cb,
                     ShellModel.ZOOM_HOME)
        self.append(icon)

        palette = Palette(_('Home'))
        palette.props.invoker = FrameCanvasInvoker(icon)
        palette.set_group_id('frame')
        icon.set_palette(palette)

        icon = IconButton(icon_name='theme:zoom-activity',
                          stroke_color=color.BLACK,
                          fill_color=color.WHITE)
        icon.connect('activated',
                     self._level_clicked_cb,
                     ShellModel.ZOOM_ACTIVITY)
        self.append(icon)

        palette = Palette(_('Activity'))
        palette.props.invoker = FrameCanvasInvoker(icon)
        palette.set_group_id('frame')
        icon.set_palette(palette)

    def _level_clicked_cb(self, item, level):
        self._shell.set_zoom_level(level)
