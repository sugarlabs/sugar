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
import sys
import gtk
import string
import gobject
import cairo
import procmem

from graphics.frequency import HorizontalGraphic

class CPU_Usage:
    _CPU_HZ = 0
    _last_jiffies = 0
    _times = 0

    def __init__(self):
        self._CPU_HZ = os.sysconf(2)

    def _get_CPU_data(self):
        # Uptime info
        stat_file = "/proc/stat"

        try:
            infile = file(stat_file, "r")
        except:
            print "Error trying uptime file"
            return -1

        stat_line = infile.readline()
        cpu_info = string.split(stat_line, ' ')
        infile.close()

        return cpu_info
    
    def _get_CPU_usage(self):
        
        cpu_info = self._get_CPU_data()
        
        used_jiffies = (int(cpu_info[2]) + int(cpu_info[3]) + int(cpu_info[4]))

        if self._times ==0:
            self._last_jiffies = used_jiffies
            self._times +=1
            return 0

        new_ujiffies = (used_jiffies - self._last_jiffies)
        new_ajiffies = ((self.frequency/1000) * self._CPU_HZ)

        if new_ajiffies <= 0:
            pcpu = 0.0
        else:
            pcpu = ((new_ujiffies*100)/new_ajiffies)

        if pcpu >100:
            pcpu = 100

        self._times +=1
        self._last_jiffies = used_jiffies

        return pcpu

class XO_CPU(gtk.Frame):
    _frequency_timer = 1

    def __init__(self):
        gtk.Frame.__init__(self, 'System CPU Usage')
        self.set_border_width(10)

        width = (gtk.gdk.screen_width() * 99 / 100) - 50
        height = (gtk.gdk.screen_height() * 15 / 100) - 20

        # Create graphic
        self._graphic = HorizontalGraphic()
        self._graphic.set_size_request(width, height)

        fixed = gtk.Fixed()
        fixed.set_border_width(10)
        fixed.add(self._graphic)

        self.add(fixed)

        self._DRW_CPU = CPU_Usage()
        self._DRW_CPU.frequency = 1000 # 1 Second

        gobject.timeout_add(self._DRW_CPU.frequency, self._update_cpu_usage)

    def _update_cpu_usage(self):
        print "update XO CPU"
        self._cpu = self._DRW_CPU._get_CPU_usage()
        self.set_label('System CPU Usage: ' + str(self._cpu) + '%')

        # Draw the value into the graphic
        self._graphic.draw_value(self._cpu)

        return True
