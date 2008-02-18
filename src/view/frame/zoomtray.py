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

from sugar.graphics.palette import Palette
from sugar.graphics.radiotoolbutton import RadioToolButton
from sugar.graphics.tray import HTray

from view.frame.frameinvoker import FrameWidgetInvoker
from model.shellmodel import ShellModel

class ZoomTray(HTray):
    def __init__(self, shell):
        HTray.__init__(self)

        self._shell = shell

        shell_model = shell.get_model()
        shell_model.connect('notify::zoom-level', self.__notify_zoom_level_cb)

        self._mesh_button = self._add_button('zoom-neighborhood',
                _('Neighborhood'), ShellModel.ZOOM_MESH)
        self._groups_button = self._add_button('zoom-groups',
                _('Group'), ShellModel.ZOOM_FRIENDS)
        self._home_button = self._add_button('zoom-home',
                _('Home'), ShellModel.ZOOM_HOME)
        self._activity_button = self._add_button('zoom-activity',
                _('Activity'), ShellModel.ZOOM_ACTIVITY)

    def _add_button(self, icon_name, label, zoom_level):
        if self.get_children():
            group = self.get_children()[0]
        else:
            group = None

        button = RadioToolButton(named_icon=icon_name, group=group)
        button.connect('clicked', self._level_clicked_cb, zoom_level)
        self.add_item(button)
        button.show()

        palette = Palette(label)
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)
        
        return button

    def _level_clicked_cb(self, button, level):
        self._shell.set_zoom_level(level)

    def __notify_zoom_level_cb(self, model, pspec):
        new_level = model.props.zoom_level

        if new_level == ShellModel.ZOOM_MESH:
            self._mesh_button.props.active = True
        elif new_level == ShellModel.ZOOM_FRIENDS:
            self._groups_button.props.active = True
        elif new_level == ShellModel.ZOOM_HOME:
            self._home_button.props.active = True
        elif new_level == ShellModel.ZOOM_ACTIVITY:
            self._activity_button.props.active = True

