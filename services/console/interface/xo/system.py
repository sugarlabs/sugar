#!/usr/bin/env python

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

class XO_System(gtk.Fixed):
    
    def __init__(self):
        gtk.Fixed.__init__(self)
        self.set_border_width(10)
        
        build = self._get_system_build()
        label_build = gtk.Label('OLPC Build: ' + str(build))

        hbox = gtk.HBox(False, 0)
        hbox.pack_start(label_build, False, False, 5)
        
        fixed_border = gtk.Fixed()
        fixed_border.set_border_width(8)
        fixed_border.add(hbox)
        
        frame = gtk.Frame('System Information')
        frame.add(fixed_border)
        
        self.add(frame)
        self.show_all()

    def _get_system_build(self):
        build_file_path = '/boot/olpc_build'
        
        try:
            f = open(build_file_path, 'r')
            build = f.read()
            f.close()
            return build
        except:
            return "None"
