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
import pango

class XO_System(gtk.Fixed):
        
    def __init__(self):
        gtk.Fixed.__init__(self)
        self.set_border_width(12)
        
        table = gtk.Table(2, 2)
        table.set_border_width(15)
        table.set_col_spacings(7)
        table.set_row_spacings(7)
    
        # BUILD
        build = self._get_system_build()
        label_build = self.get_label('OLPC Build:')
        label_build_value = self.get_label(build)
        
        # KERNEL
        sysinfo = os.uname()
        label_kernel = self.get_label('Kernel Version: ')
        label_kernel_value = self.get_label(sysinfo[0] + '-' + sysinfo[2])

        # OLPC Build
        table.attach(label_build, 0, 1, 0, 1)
        table.attach(label_build_value, 1,2, 0,1)
        
        # Kernel Version
        table.attach(label_kernel, 0, 1, 1, 2)
        table.attach(label_kernel_value, 1, 2, 1, 2)
        
        frame = gtk.Frame('System Information')
        frame.add(table)
        
        self.add(frame)
        self.show_all()

    def _get_system_build(self):
        build_file_path = '/boot/olpc_build'
        
        try:
            f = open(build_file_path, 'r')
            build = int(f.read())
            f.close()
            
            return build
        except:
            return "None"

    def get_label(self, string):
        label = gtk.Label(string)
        label.set_alignment(0.0, 0.5)
        label.modify_font(self._set_font())
        return label

    def _set_font(self):
        font = pango.FontDescription('Sans 8')
        font.set_weight(pango.WEIGHT_NORMAL)
        
        return font
