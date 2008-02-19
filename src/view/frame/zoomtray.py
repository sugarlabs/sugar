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
import logging

import gtk

from sugar.graphics.palette import Palette
from sugar.graphics.radiotoolbutton import RadioToolButton

from view.frame.frameinvoker import FrameWidgetInvoker
from model.shellmodel import ShellModel

class ZoomTray(gtk.HBox):
    def __init__(self, shell):
        gtk.HBox.__init__(self)

        self._shell = shell

        self._mesh_button = self._add_button('zoom-neighborhood',
                _('Neighborhood'), ShellModel.ZOOM_MESH)
        self._groups_button = self._add_button('zoom-groups',
                _('Group'), ShellModel.ZOOM_FRIENDS)
        self._home_button = self._add_button('zoom-home',
                _('Home'), ShellModel.ZOOM_HOME)
        self._activity_button = self._add_button('zoom-activity',
                _('Activity'), ShellModel.ZOOM_ACTIVITY)

        shell_model = shell.get_model()
        self._set_zoom_level(shell_model.props.zoom_level)
        shell_model.connect('notify::zoom-level', self.__notify_zoom_level_cb)

    def _add_button(self, icon_name, label, zoom_level):
        logging.debug('ZoomTray._add_button: %r %r %r' % (icon_name, label, zoom_level))
        if self.get_children():
            group = self.get_children()[0]
        else:
            group = None

        button = RadioToolButton(named_icon=icon_name, group=group)
        button.connect('toggled', self.__level_toggled_cb, zoom_level)
        self.pack_start(button)
        button.show()

        palette = Palette(label)
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)
        
        return button

    def __level_toggled_cb(self, button, zoom_level):
        if not button.get_active():
            return
        logging.debug('ZoomTray.__level_clicked_cb: %r' % zoom_level)
        if self._shell.get_model().props.zoom_level != zoom_level:
            self._shell.set_zoom_level(zoom_level)

    def __notify_zoom_level_cb(self, model, pspec):
        logging.debug('ZoomTray.__notify_zoom_level_cb: %r' % model.props.zoom_level)
        self._set_zoom_level(model.props.zoom_level)

    def _set_zoom_level(self, new_level):
        logging.debug('new zoom level: %r' % new_level)
        if new_level == ShellModel.ZOOM_MESH:
            self._mesh_button.props.active = True
        elif new_level == ShellModel.ZOOM_FRIENDS:
            self._groups_button.props.active = True
        elif new_level == ShellModel.ZOOM_HOME:
            self._home_button.props.active = True
        elif new_level == ShellModel.ZOOM_ACTIVITY:
            self._activity_button.props.active = True
        else:
            raise ValueError('Invalid zoom level: %r' % (new_level))

