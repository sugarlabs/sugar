# Copyright (C) 2008 One Laptop Per Child
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

import gtk
from gettext import gettext as _

from sugar.graphics.icon import Icon
from sugar.graphics import style
from sugar import profile

class ModalAlert(gtk.Window):    

    __gtype_name__ = 'SugarModalAlert'

    def __init__(self):
        gtk.Window.__init__(self)

        self.set_border_width(style.LINE_WIDTH)
        offset = style.GRID_CELL_SIZE
        width = gtk.gdk.screen_width() - offset * 2
        height = gtk.gdk.screen_height() - offset * 2
        self.set_size_request(width, height)
        self.set_position(gtk.WIN_POS_CENTER_ALWAYS) 
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_modal(True)
        
        self._main_view = gtk.EventBox()
        self._vbox = gtk.VBox()        
        self._vbox.set_spacing(style.DEFAULT_SPACING)
        self._vbox.set_border_width(style.GRID_CELL_SIZE * 2)
        self._main_view.modify_bg(gtk.STATE_NORMAL, 
                                  style.COLOR_BLACK.get_gdk_color())
        self._main_view.add(self._vbox)
        self._vbox.show()

        icon = Icon(icon_name='activity-journal',
                    pixel_size=style.XLARGE_ICON_SIZE,
                    xo_color=profile.get_color())
        self._vbox.pack_start(icon, False)
        icon.show()

        self._title = gtk.Label()
        self._title.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_WHITE.get_gdk_color())
        self._title.set_markup('<b>%s</b>' % _('Your Journal is full'))  
        self._vbox.pack_start(self._title, False)
        self._title.show()

        self._message = gtk.Label(_('Please delete some old Journal' 
                                    ' entries to make space for new ones.'))
        self._message.modify_fg(gtk.STATE_NORMAL, 
                              style.COLOR_WHITE.get_gdk_color())
        self._vbox.pack_start(self._message, False)        
        self._message.show()

        alignment = gtk.Alignment(xalign=0.5, yalign=0.5)
        self._vbox.pack_start(alignment, expand=False)
        alignment.show()

        self._show_journal = gtk.Button()
        self._show_journal.set_label(_('Show Journal'))
        alignment.add(self._show_journal)
        self._show_journal.show()
        self._show_journal.connect('clicked', self.__show_journal_cb)

        self.add(self._main_view)
        self._main_view.show()

        self.connect("realize", self.__realize_cb)

    def __realize_cb(self, widget):
        self.window.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
        self.window.set_accept_focus(True)

    def __show_journal_cb(self, button):
        '''The opener will listen on the destroy signal
        '''
        self.destroy()

