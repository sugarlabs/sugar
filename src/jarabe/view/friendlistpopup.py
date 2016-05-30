# Copyright (C) 2016 Abhijit Patel
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

from gi.repository import Gtk
from gi.repository import GObject

from sugar3.graphics.popwindow import PopWindow
from sugar3.graphics.toolbutton import ToolButton

class FriendListPopup(PopWindow):
    __gtype_name__ = 'FriendListPopup'

    __gsignals__ = {
        'friend-selected': (GObject.SignalFlags.RUN_FIRST, None,
                            ([object])),
    }

    def __init__(self):
        PopWindow.__init__(self, True)
        self.view = FriendListView()
        self._scrolled_window = Gtk.ScrolledWindow()
        self._scrolled_window.set_policy(Gtk.PolicyType.AUTOMATIC,
                                         Gtk.PolicyType.AUTOMATIC)

        self._scrolled_window.add(self.view)
        width, height = PopWindow.FULLSCREEN
        self.set_size_request(width*1/3, height*2/3)
        self.modify_fg(Gtk.StateType.NORMAL,
                       style.COLOR_BLACK.get_gdk_color())
        self.get_vbox().pack_start(self._scrolled_window, True, True, 0)
        self.get_title_box().props.title = 'Send to'
        self._scrolled_window.show()
        self.view.show()
        self.show()

        ok_button = ToolButton(icon_name='document-send')
        self.get_title_box().add_widget(ok_button, False, -1)
        ok_button.connect('clicked', self.__send_clicked_cb)
        ok_button.show()

    def __send_clicked_cb(self, button):
        model = self.view.get_model()
        selected = model.get_selected()
        self.emit('friend-selected', selected)
        self.destroy()
