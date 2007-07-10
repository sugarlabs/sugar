# Copyright (C) 2007, Eduardo Silva (edsiper@gmail.com).
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
import gtk
import gobject
import gtk.gdk
import cairo
import string

from cpu import XO_CPU
from system import XO_System
from battery import XO_Battery
from nandflash import XO_NandFlash

class Interface:
        
    def __init__(self):
        self.widget = self.vbox = gtk.VBox(False, 3)

        # System information
        xo_system = XO_System()
        self.vbox.pack_start(xo_system, False, False, 0)

        # CPU usage / Graph
        xo_cpu = XO_CPU()
        self.vbox.pack_start(xo_cpu, False, False, 0)

        # Graphics: Battery Status, NandFlash
        self._xo_nandflash = XO_NandFlash()

        hbox = gtk.HBox(False, 2)
        hbox.pack_start(self._xo_nandflash, False, False, 0)

        self.vbox.pack_start(hbox, False, False, 0)
        self.vbox.show_all()

        # Update every 5 seconds
        gobject.timeout_add(5000, self._update_components)

    def _update_components(self):
        self._xo_battery.update_status()
        self._xo_nandflash.update_status()

        return True

