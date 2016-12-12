# Copyright (C) 2006-2007 Red Hat, Inc.
# Copyright (C) 2009 Simon Schampijer
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from gettext import gettext as _
import logging

from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics import style
from sugar3.graphics.palette import Palette
from sugar3.graphics.radiotoolbutton import RadioToolButton

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import shell


class ZoomToolbar(Gtk.Toolbar):
    __gsignals__ = {
        'level-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                          ([]))
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        # we shouldn't be mirrored in RTL locales
        self.set_direction(Gtk.TextDirection.LTR)

        # ask not to be collapsed if possible
        self.set_size_request(4 * style.GRID_CELL_SIZE, -1)

        self._mesh_button = self._add_button('zoom-neighborhood',
                                             _('Neighborhood'),
                                             _('F1'),
                                             shell.ShellModel.ZOOM_MESH)
        self._groups_button = self._add_button('zoom-groups',
                                               _('Group'),
                                               _('F2'),
                                               shell.ShellModel.ZOOM_GROUP)
        self._home_button = self._add_button('zoom-home',
                                             _('Home'),
                                             _('F3'),
                                             shell.ShellModel.ZOOM_HOME)
        self._activity_button = \
            self._add_button('zoom-activity',
                             _('Activity'),
                             _('F4'),
                             shell.ShellModel.ZOOM_ACTIVITY)

        shell_model = shell.get_model()
        self._set_zoom_level(shell_model.zoom_level)
        shell_model.zoom_level_changed.connect(self.__zoom_level_changed_cb)

    def _add_button(self, icon_name, label, accelerator, zoom_level):
        if self.get_children():
            group = self.get_children()[0]
        else:
            group = None

        button = RadioToolButton(icon_name=icon_name, group=group,
                                 accelerator=accelerator)
        button.connect('clicked', self.__level_clicked_cb, zoom_level)
        self.add(button)
        button.show()

        palette = Palette(GLib.markup_escape_text(label))
        palette.props.invoker = FrameWidgetInvoker(button)
        palette.set_group_id('frame')
        button.set_palette(palette)

        return button

    def __level_clicked_cb(self, button, level):
        if not button.get_active():
            return

        shell.get_model().set_zoom_level(level)
        self.emit('level-clicked')

    def __zoom_level_changed_cb(self, **kwargs):
        self._set_zoom_level(kwargs['new_level'])

    def _set_zoom_level(self, new_level):
        logging.debug('new zoom level: %r', new_level)
        if new_level == shell.ShellModel.ZOOM_MESH:
            self._mesh_button.props.active = True
        elif new_level == shell.ShellModel.ZOOM_GROUP:
            self._groups_button.props.active = True
        elif new_level == shell.ShellModel.ZOOM_HOME:
            self._home_button.props.active = True
        elif new_level == shell.ShellModel.ZOOM_ACTIVITY:
            self._activity_button.props.active = True
        else:
            raise ValueError('Invalid zoom level: %r' % (new_level))
