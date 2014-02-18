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
from sugar3.graphics import style
from sugar3.graphics.xocolor import XoColor


from jarabe.controlpanel.sectionview import SectionView

from backupmanager import BackupManager


class BackupView(SectionView):
    __gtype_name__ = 'SugarBackupWindow'

    def __init__(self, model, alerts=None):
        SectionView.__init__(self)

        # add the initial panel
        self.set_canvas(SelectBackupRestorePanel())
        self.grab_focus()
        self.show_all()
        self._manager = BackupManager()

    def set_canvas(self, canvas):
        if len(self.get_children()) > 0:
            self.remove(self.get_children()[0])
        if canvas:
            logging.error('adding canvas %s', canvas)
            self.add(canvas)


class _BackupButton(Gtk.EventBox):

    __gproperties__ = {
        'icon-name': (str, None, None, None, GObject.PARAM_READWRITE),
        'pixel-size': (object, None, None, GObject.PARAM_READWRITE),
        'title': (str, None, None, None, GObject.PARAM_READWRITE),
    }

    def __init__(self, **kwargs):
        self._icon_name = None
        self._pixel_size = style.GRID_CELL_SIZE
        self._xo_color = None
        self._title = 'No Title'

        Gtk.EventBox.__init__(self, **kwargs)

        self._vbox = Gtk.VBox()
        self._icon = Icon(icon_name=self._icon_name,
                          pixel_size=self._pixel_size,
                          xo_color=XoColor('#000000,#000000'))
        self._vbox.pack_start(self._icon, expand=False, fill=False, padding=0)

        self._label = Gtk.Label(label=self._title)
        self._vbox.pack_start(self._label, expand=False, fill=False, padding=0)

        self._vbox.set_spacing(style.DEFAULT_SPACING)
        self.set_visible_window(False)
        self.set_app_paintable(True)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)

        self.add(self._vbox)
        self._vbox.show()
        self._label.show()
        self._icon.show()

    def get_icon(self):
        return self._icon

    def do_set_property(self, pspec, value):
        if pspec.name == 'icon-name':
            if self._icon_name != value:
                self._icon_name = value
        elif pspec.name == 'pixel-size':
            if self._pixel_size != value:
                self._pixel_size = value
        elif pspec.name == 'title':
            if self._title != value:
                self._title = value

    def do_get_property(self, pspec):
        if pspec.name == 'icon-name':
            return self._icon_name
        elif pspec.name == 'pixel-size':
            return self._pixel_size
        elif pspec.name == 'title':
            return self._title


class SelectBackupRestorePanel(Gtk.VBox):

    def __init__(self):
        Gtk.VBox.__init__(self)

        hbox = Gtk.HBox()

        self.backup_btn = _BackupButton(
            icon_name='backup-backup',
            title=_('Save the contents of your Journal'),
            pixel_size=style.GRID_CELL_SIZE)
        hbox.pack_start(self.backup_btn, False, False, style.DEFAULT_SPACING)

        self.restore_btn = _BackupButton(
            icon_name='backup-restore',
            title=_('Restore the contents of your Journal'),
            pixel_size=style.GRID_CELL_SIZE)

        hbox.pack_start(self.restore_btn, False, False, style.DEFAULT_SPACING)
        hbox.set_valign(Gtk.Align.CENTER)
        hbox.set_halign(Gtk.Align.CENTER)
        self.add(hbox)
        self.show_all()
