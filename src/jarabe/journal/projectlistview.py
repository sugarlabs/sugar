# Copyright (C) 2016, Abhijit Patel
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

import logging
from gettext import gettext as _

from sugar3.graphics import iconentry
from gi.repository import Gtk
from gi.repository import GObject
from jarabe.journal.detailview import BackBar

class ProjectListView(Gtk.VBox):
    back_to_main_signal = GObject.Signal('back-to-main',
                                     arg_types=([]))

    def __init__(self):
        Gtk.VBox.__init__(self)
        logging.debug('[GSoC]ProjectListView constructor')
        back_bar = BackBar()
        back_bar.connect('button-release-event',
                         self.__back_bar_release_event_cb)
        self.pack_start(back_bar, False, True, 0)

        entry = iconentry.IconEntry()
        entry.set_icon_from_name(iconentry.ICON_ENTRY_PRIMARY,
                                             'activity-journal')
        text = _('Add new project')
        entry.set_placeholder_text(text)
        entry.add_clear_button()
        self.pack_start(entry, False, True, 0)
        self.show_all()

    def __back_bar_release_event_cb(self, back_bar, event):
        logging.debug('[GSoC]Back button pressed')
        self.back_to_main_signal.emit()



