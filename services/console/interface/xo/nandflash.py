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

import gtk
import gobject

from os import statvfs
from label import Label
from graphics.box import *

class XO_NandFlash(gtk.Fixed):
    _MOUNT_POINT = '/'

    def __init__(self):
        gtk.Fixed.__init__(self)
        
        self._frame_text = 'Nand Flash'
        self._frame = gtk.Frame(self._frame_text)
        self.set_border_width(10)
        

        self._nandflash_box = BoxGraphic(color_mode=COLOR_MODE_REVERSE)
        self._nandflash_box.set_size_request(70, 150)

        fixed = gtk.Fixed();
        fixed.set_border_width(10)
        fixed.add(self._nandflash_box)

        hbox = gtk.HBox(False, 0)
        hbox.pack_start(fixed, False, False, 4)

        # Battery info
        table = gtk.Table(2, 3)
        table.set_border_width(5)
        table.set_col_spacings(7)
        table.set_row_spacings(7)

        label_total_size = Label('Total: ' , Label.DESCRIPTION)
        self._label_total_value = Label('0 KB', Label.DESCRIPTION)

        label_used_size = Label('Used: ' , Label.DESCRIPTION)
        self._label_used_value = Label('0 KB', Label.DESCRIPTION)

        label_free_size = Label('Free: ' , Label.DESCRIPTION)
        self._label_free_value = Label('0 KB', Label.DESCRIPTION)

        # Total
        table.attach(label_total_size, 0, 1, 0, 1)
        table.attach(self._label_total_value, 1,2, 0,1)
        # Used
        table.attach(label_used_size, 0, 2, 1, 2)
        table.attach(self._label_used_value, 1,3, 1,2)
        # Free
        table.attach(label_free_size, 0, 3, 2, 3)
        table.attach(self._label_free_value, 1,4, 2,3)

        alignment = gtk.Alignment(0,0,0,0)
        alignment.add(table)

        hbox.pack_start(alignment, False, False, 0)
        self._frame.add(hbox)
        self.add(self._frame)
        self.show()
        self.update_status()

    def update_status(self):
        nand = StorageDevice(self._MOUNT_POINT)

        # Byte values
        total = (nand.f_bsize*nand.f_blocks)
        free = (nand.f_bsize*nand.f_bavail)
        used = (total - free)

        self._label_total_value.set_label(str(total/1024) + ' KB')
        self._label_used_value.set_label(str(used/1024) + ' KB')
        self._label_free_value.set_label(str(free/1024) + ' KB')
        self._usage_percent = ((used*100)/total)
        
        frame_label = self._frame_text + ': ' + str(self._usage_percent) + '%'
        self._frame.set_label(frame_label)
        self._nandflash_box.set_capacity(self._usage_percent)

class StorageDevice:
    f_bsize = 0
    f_frsize = 0
    f_blocks = 0
    f_bfree = 0
    f_bavail = 0
    f_files = 0
    f_ffree = 0
    f_favail = 0
    f_flag = 0
    f_namemax = 0

    def __init__(self, mount_point):
        self.f_bsize, self.f_frsize, self.f_blocks, self.f_bfree, \
            self.f_bavail, self.f_files, self.f_ffree, \
            self.f_favail, self.f_flag, self.f_namemax = statvfs(mount_point)

"""
w = gtk.Window()
a = XO_NandFlash()
w.add(a)
w.show_all()
gtk.main()
"""
