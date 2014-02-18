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

from gi.repository import Gtk

from sugar3.graphics.icon import Icon
from sugar3.graphics import style

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


class BigButton(Gtk.Button):

    def __init__(self, _icon_name, label):
        Gtk.Button.__init__(self)
        _icon = Icon(icon_name=_icon_name,
                     pixel_size=style.MEDIUM_ICON_SIZE)
        self.set_label(label)
        self.set_image(_icon)
        self.set_image_position(Gtk.PositionType.TOP)


class SelectBackupRestorePanel(Gtk.VBox):

    def __init__(self):
        Gtk.VBox.__init__(self)

        hbox = Gtk.HBox()

        self.backup_btn = BigButton(
            'backup', _('Make a safe copy of the content of your Journal'))
        hbox.pack_start(self.backup_btn, False, False, style.DEFAULT_SPACING)

        self.restore_btn = BigButton(
            'restore', _('Restore a security copy into your Journal'))
        hbox.pack_start(self.restore_btn, False, False, style.DEFAULT_SPACING)
        hbox.set_valign(Gtk.Align.CENTER)
        hbox.set_halign(Gtk.Align.CENTER)
        self.add(hbox)
        self.show_all()
