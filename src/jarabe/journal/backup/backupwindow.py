# Copyright (C) 2013, SugarLabs
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.

import logging
from gettext import gettext as _

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk

from sugar3.graphics.icon import Icon
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics import style

from jarabe.model import shell
from backupmanager import BackupManager


class BackupWindow(Gtk.Window):
    __gtype_name__ = 'SugarBackupWindow'

    def __init__(self):
        Gtk.Window.__init__(self)

        self.set_border_width(style.LINE_WIDTH)
        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)

        self._vbox = Gtk.VBox()
        # add the toolbar
        self._main_toolbar = MainToolbar()
        self._main_toolbar.show()
        self._main_toolbar.connect('stop-clicked',
                                   self.__stop_clicked_cb)

        self._vbox.pack_start(self._main_toolbar, False, False, 0)

        # add a container to set the canvas
        self._main_view = Gtk.EventBox()
        self._vbox.pack_start(self._main_view, True, True, 0)
        self._main_view.modify_bg(Gtk.StateType.NORMAL,
                                  style.COLOR_BLACK.get_gdk_color())

        self.add(self._vbox)

        width = Gdk.Screen.width() - style.GRID_CELL_SIZE * 2
        height = Gdk.Screen.height() - style.GRID_CELL_SIZE * 2
        self.set_size_request(width, height)
        self.connect('realize', self.__realize_cb)

        # add the initial panel
        self._set_canvas(SelectBackupRestorePanel())
        self.grab_focus()
        self.show_all()
        self._manager = BackupManager()

    def __realize_cb(self, widget):
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.get_window().set_accept_focus(True)
        # the modal windows counter is updated to disable hot keys - SL#4601
        shell.get_model().push_modal()

    def grab_focus(self):
        # overwrite grab focus in order to grab focus on the view
        if self._main_view.get_child() is not None:
            self._main_view.get_child().grab_focus()

    def __stop_clicked_cb(self, widget):
        # TODO: request confirmation and cancel operation if needed
        shell.get_model().pop_modal()
        self.destroy()

    def _set_canvas(self, canvas):
        if self._main_view.get_child() is not None:
            self._main_view.remove(self._main_view.get_child())
        if canvas:
            logging.error('adding canvas %s', canvas)
            self._main_view.add(canvas)


class MainToolbar(Gtk.Toolbar):
    """ Main toolbar of the backup/restore window
    """
    #__gtype_name__ = 'MainToolbar'

    __gsignals__ = {
        'stop-clicked': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         ([])),
    }

    def __init__(self):
        Gtk.Toolbar.__init__(self)

        separator = Gtk.SeparatorToolItem()
        separator.props.draw = False
        separator.set_expand(True)
        self.insert(separator, -1)
        separator.show()

        self.stop = ToolButton(icon_name='dialog-cancel')
        self.stop.set_tooltip(_('Done'))
        self.stop.connect('clicked', self.__stop_clicked_cb)
        self.stop.show()
        self.insert(self.stop, -1)
        self.stop.show()

    def __stop_clicked_cb(self, button):
        self.emit('stop-clicked')


class WhiteLabel(Gtk.Label):

    def __init__(self, text):
        Gtk.Label.__init__(self)
        markup = '<span foreground="white">%s</span>' % text
        self.set_markup(markup)


class BigButton(Gtk.Button):

    def __init__(self, _icon_name):
        Gtk.Button.__init__(self)
        _icon = Icon(icon_name=_icon_name,
                     pixel_size=style.XLARGE_ICON_SIZE)
        self.add(_icon)
        self.modify_bg(Gtk.StateType.NORMAL,
                       style.COLOR_BLACK.get_gdk_color())


class SelectBackupRestorePanel(Gtk.HBox):

    def __init__(self):
        Gtk.HBox.__init__(self)

        vbox = Gtk.VBox()
        self.backup_btn = BigButton('backup')
        label = WhiteLabel(
            _('Make a safe copy of the content of your Journal'))
        vbox.add(self.backup_btn)
        vbox.add(label)
        self.add(vbox)

        vbox = Gtk.VBox()
        self.restore_btn = BigButton('restore')
        label = WhiteLabel(_('Restore a security copy into your Journal'))
        vbox.add(self.restore_btn)
        self.add(vbox)

        self.show_all()

        vbox.add(label)
