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

from sugar4.graphics import style
from sugar4.graphics.palette import Palette
from sugar4.graphics.radiotoolbutton import RadioToolButton

from jarabe.frame.frameinvoker import FrameWidgetInvoker
from jarabe.model import shell


class ZoomToolbar(Gtk.Box):
    __gtype_name__ = 'SugarZoomToolbar'

    __gsignals__ = {
        'level-clicked': (GObject.SignalFlags.RUN_FIRST, None,
                          ([]))
    }

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.add_css_class('toolbar')

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
        group = self.get_first_child()

        button = RadioToolButton(icon_name=icon_name, group=group,
                                 accelerator=accelerator)
        button.connect('toggled', self.__level_toggled_cb, zoom_level)
        self.append(button)

        invoker = FrameWidgetInvoker(button)
        palette = Palette(label)
        invoker.palette = palette
        palette.set_group_id('frame')
        button.set_palette_invoker(invoker)

        return button

    def __level_toggled_cb(self, button, level):
        if not button.get_active():
            return

        model = shell.get_model()
        if level == shell.ShellModel.ZOOM_ACTIVITY and \
                model.get_active_activity() is None:
            # No activity open: show Journal instead of the empty compositor.
            from jarabe.journal import journalactivity
            journalactivity.get_journal().show_journal()
            # Restore the toolbar button to the current zoom level so the
            # toolbar stays consistent (we didn't change the zoom level).
            GLib.idle_add(self._set_zoom_level, model.zoom_level)
        else:
            model.set_zoom_level(level)

        self.emit('level-clicked')

    def __zoom_level_changed_cb(self, **kwargs):
        self._set_zoom_level(kwargs['new_level'])

    def _set_zoom_level(self, new_level):
        logging.debug('new zoom level: %r', new_level)
        if new_level == shell.ShellModel.ZOOM_MESH:
            self._mesh_button.set_active(True)
        elif new_level == shell.ShellModel.ZOOM_GROUP:
            self._groups_button.set_active(True)
        elif new_level == shell.ShellModel.ZOOM_HOME:
            self._home_button.set_active(True)
        elif new_level == shell.ShellModel.ZOOM_ACTIVITY:
            self._activity_button.set_active(True)
        else:
            raise ValueError('Invalid zoom level: %r' % (new_level))
