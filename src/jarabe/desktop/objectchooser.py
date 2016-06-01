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

from gettext import gettext as _
import logging

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import Wnck

from sugar3.graphics import style
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.toolbarbox import ToolbarBox
from sugar3.graphics.toolbutton import ToolButton
from sugar3.graphics.popwindow import PopWindow

from jarabe.desktop.activitieslist import ActivitiesList

class ObjectChooser(PopWindow):

    #__gtype_name__ = 'ObjectChooser'

    __gsignals__ = {
        'response': (GObject.SignalFlags.RUN_FIRST, None, ([int])),
    }

    def __init__(self):
        logging.debug('In the Object Chooser class init hehehe')
        PopWindow.__init__(self)

        self._list_view = ActivitiesList()
        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                         Gtk.PolicyType.AUTOMATIC)

        self._scrolled_window.add(self._list_view)

        self.get_vbox().pack_start(self._scrolled_window, True, True, 0)
        self._list_view.show()
        self._list_view._tree_view.connect('row-activated',self.__on_row_activated)
        self.show()
        logging.debug('In the Object Chooser class init ended hehehe')

    def __on_row_activated(self, treeview, path, col):
        logging.debug('[GSoC]__on_row_activated overwritten in ObjectChooser')
            
