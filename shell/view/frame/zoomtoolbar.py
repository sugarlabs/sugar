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

import gtk

from sugar.graphics.palette import Palette
from sugar.graphics.toolbutton import ToolButton

from view.frame.frameinvoker import FrameWidgetInvoker
from model.shellmodel import ShellModel

class ZoomToolbar(gtk.Toolbar):
    def __init__(self, shell):
        gtk.Toolbar.__init__(self)

        self._shell = shell

        self.set_show_arrow(False)

        button = ToolButton(icon_name='zoom-mesh')
        button.connect('clicked',
                       self._level_clicked_cb,
                       ShellModel.ZOOM_MESH)
        self.insert(button, -1)
        button.show()

        palette = Palette(_('Neighborhood'))
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)

        button = ToolButton(icon_name='zoom-friends')
        button.connect('clicked',
                       self._level_clicked_cb,
                       ShellModel.ZOOM_FRIENDS)
        self.insert(button, -1)
        button.show()

        palette = Palette(_('Group'))
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)

        button = ToolButton(icon_name='zoom-home')
        button.connect('clicked',
                       self._level_clicked_cb,
                       ShellModel.ZOOM_HOME)
        self.insert(button, -1)
        button.show()

        palette = Palette(_('Home'))
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)

        button = ToolButton(icon_name='zoom-activity')
        button.connect('clicked',
                       self._level_clicked_cb,
                       ShellModel.ZOOM_ACTIVITY)
        self.insert(button, -1)
        button.show()

        palette = Palette(_('Activity'))
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)

    def _level_clicked_cb(self, button, level):
        self._shell.set_zoom_level(level)
