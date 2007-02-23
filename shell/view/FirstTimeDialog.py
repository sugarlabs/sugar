# Copyright (C) 2006, Red Hat, Inc.
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

import os
from ConfigParser import ConfigParser

import gtk
from gettext import gettext as _

from sugar.graphics.xocolor import XoColor
from sugar import env

class FirstTimeDialog(gtk.Dialog):
    def __init__(self):
        gtk.Dialog.__init__(self)

        label = gtk.Label(_('Nick Name:'))
        label.set_alignment(0.0, 0.5)
        self.vbox.pack_start(label)
        label.show()

        self._entry = gtk.Entry()
        self._entry.connect('changed', self._entry_changed_cb)
        self._entry.connect('activate', self._entry_activated_cb)
        self.vbox.pack_start(self._entry)
        self._entry.show()

        self._ok = gtk.Button(None, gtk.STOCK_OK)
        self._ok.set_sensitive(False)
        self.vbox.pack_start(self._ok)
        self._ok.connect('clicked', self._ok_button_clicked_cb)
        self._ok.show()

    def _entry_changed_cb(self, entry):
        valid = (len(entry.get_text()) > 0)
        self._ok.set_sensitive(valid)

    def _entry_activated_cb(self, entry):
        self._create_buddy_section()
        
    def _ok_button_clicked_cb(self, button):
        self._create_buddy_section()
        
    def _create_buddy_section(self):
        cp = ConfigParser()

        section = 'Buddy'    
        cp.add_section(section)
        cp.set(section, 'NickName', self._entry.get_text())
        cp.set(section, 'Color', XoColor().to_string())

        config_path = os.path.join(env.get_profile_path(), 'config')
        fileobject = open(config_path, 'w')
        cp.write(fileobject)
        fileobject.close()

        self.destroy()
