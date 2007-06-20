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

from label import Label
from label import Style

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
        label_build = Label('OLPC Build:', Label.DESCRIPTION)
        label_build_value = Label(str(build), Label.DESCRIPTION)
        
        # FIRMWARE
        firmware = self._get_firmware_version()
        label_firmware = Label('XO Firmware:', Label.DESCRIPTION)
        label_firmware_value = Label(firmware, Label.DESCRIPTION)

        # KERNEL
        sysinfo = os.uname()
        label_kernel = Label('Kernel Version:', Label.DESCRIPTION)
        label_kernel_value = Label(sysinfo[0] + '-' + sysinfo[2], Label.DESCRIPTION)

        # OLPC Build
        table.attach(label_build, 0, 1, 0, 1)
        table.attach(label_build_value, 1,2, 0,1)

        # XO Firmware
        table.attach(label_firmware, 0, 1, 1, 2)
        table.attach(label_firmware_value, 1, 2, 1, 2)

        # Kernel Version
        table.attach(label_kernel, 0, 1, 2, 3)
        table.attach(label_kernel_value, 1, 2, 2, 3)
        
        frame = gtk.Frame('System Information')
        style = Style()
        style.set_title_font(frame);
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

    # Get XO Firmware Versions
    def _get_firmware_version(self):

        try:
            # Shell command            
            cmd = "/usr/sbin/olpc-bios-sig"

            data = os.popen(cmd).readlines()
            return data[0].strip()
        except:
            return "None"

