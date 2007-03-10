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
import sys
import gtk
import string
import gobject
import drwarea

class CPU_Usage:
    
    CPU_HZ = 0
    last_jiffies = 0
    times = 0
    
    def __init__(self):
        self.CPU_hz = os.sysconf(2)
        
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
        
        if self.times ==0:
            self.last_jiffies = used_jiffies
            self.times +=1
            return True
        
        new_ujiffies = (used_jiffies - self.last_jiffies)
        new_ajiffies = ((self.frequency/1000) * self.CPU_hz)

        if new_ajiffies <= 0:
            pcpu = 0.0
        else:
            pcpu = ((new_ujiffies*100)/new_ajiffies)

        if pcpu >100:
            pcpu = 100
            
        self.times +=1
        self.last_jiffies = used_jiffies
        
        return pcpu
        
class XO_CPU(gtk.Frame):
    
    context = None
    frequency_timer = 1
    graph_offset = 7        
        
    def __init__(self):
        gtk.Frame.__init__(self, 'System CPU Usage')
        self.set_border_width(10)

        self._updated = False
        self.drw_width = (gtk.gdk.screen_width() * 99 / 100) - 50
        self.drw_height = (gtk.gdk.screen_height() * 15 / 100) - 20

        self.y_cpu = self.drw_height - self.graph_offset
        self._cpu = 0
        self._cpu_buffer = [0]

        self._drawingarea = gtk.DrawingArea()
        self._drawingarea.set_size_request(self.drw_width, self.drw_height)
        self._drawingarea.connect("expose-event", self.do_expose)

        self.dat = drwarea.Drawing_Area_Tools(self._drawingarea)
        
        fixed = gtk.Fixed()
        fixed.set_border_width(10)
        fixed.add(self._drawingarea)
        
        self.add(fixed)
        
        DRW_CPU = CPU_Usage()
        DRW_CPU.frequency = 1000 # 1 Second

        gobject.timeout_add(DRW_CPU.frequency, self._update_cpu_usage, DRW_CPU)

    def _update_cpu_usage(self, DRW_CPU):
        
        redraw_all = False
        
        # end of the drawing area
        if ((self.frequency_timer + 1)*self.graph_offset) >= (self.drw_width - self.graph_offset):
            self.frequency_timer = 1
            self._cpu_buffer = [self._cpu_buffer[-1]]
            redraw_all = True
            length = 1
        else:
            length = len(self._cpu_buffer) - 1

        self._cpu = DRW_CPU._get_CPU_usage()
        self._cpu_buffer.append(self._cpu)

        self._updated = True

        if redraw_all:
            area_x = 0
            area_width = self.drw_width
        else:
            area_x = (length*self.graph_offset)
            area_width = self.graph_offset*2

        self._drawingarea.queue_draw_area(area_x, 0, area_width, self.drw_height - 5)
        self.frequency_timer += 1

        return True
    
    def _get_y_cpu(self, pcpu):

        height = (self.dat.range_y['to']) - (self.dat.range_y['from'])
        
        # Get percent of cpu usage
        y_value	= (height - ((pcpu*height)/100) + 4)

        return int(y_value) 
    
    def do_expose(self, widget, event):
        context = widget.window.cairo_create()        

        context.rectangle(0, 0, self.dat.width - 1, self.dat.height - 1)
        context.set_source_rgb (0,0,0)
        context.fill_preserve()

        if event.area.x == 0:
            draw_all = True
        else:
            draw_all = False
            
        context.rectangle(event.area.x, event.area.y, event.area.width, event.area.height)
        context.clip()
    
        # Drawing horizontal and vertical border lines
        self.dat.draw_border_lines(context)
            
        # Drawing grid
        line_margin = self.dat.margin
        context.set_source_rgb(1, 1, 1)
        context.set_line_width(1)
        #self.draw_grid(context, event, line_margin + 1, line_margin + 1, self.dat.width - line_margin - 2, self.dat.height - line_margin - 2)

        self._draw_buffer(event, widget, context, draw_all)

        cpu_label = str(round(self._cpu, 4))
        self.set_label('System CPU Usage: ' + cpu_label + ' %')

        self._updated = False
        return False

    # Draw a grid
    def draw_grid(self, context, event, init_x, init_y, end_x, end_y):
    
        x_range = (end_x - init_x) + 5
        y_range = (end_y - init_y) + 1
        
        current_y = init_y
        context.set_line_width(0.3)
        
        #for y in range(y_range):
        for y in range(0, y_range, 20):
            if (y%20) == 0:
                context.move_to(init_x, y)
                context.line_to(end_x, y)

        for x in range(0, x_range, 20):
            if (x%20) == 0:
                context.move_to(x, init_y)
                context.line_to(x, end_y)
        
        context.stroke()
    
    def check_context(self, event, offset, length, freq):
        print "CONTEXT ALLOWED - from: " + str(event.area.x) + " to: " + str(event.area.x+event.area.width)
        
        if event.area.x != (freq*self.graph_offset):
            print "************************"
            print " ERROR DRAWING CONTEXT"
            print " ---> Area X: " + str(event.area.x) + " To X: " + str(freq*self.graph_offset)
            print "************************"
            
    def _draw_buffer(self, event, drwarea, context, draw_all=True):
        buffer_offset = 0
        freq = 1 # Frequency timer

        length = len(self._cpu_buffer)
        
        if length == 0:
            return
        
        # Context properties
        context.set_line_width(2)
        context.set_source_rgb(0,1,0)
        
        if draw_all == True:
            buffer_offset = 0
            freq = 0
        else:
            freq = buffer_offset = (event.area.x/self.graph_offset)

        for pcpu in self._cpu_buffer[buffer_offset:length]:
            if buffer_offset == 0:
                from_y = self.drw_height - self.graph_offset
                from_x = self.graph_offset
            else:
                from_y = self._get_y_cpu(self._cpu_buffer[buffer_offset-1])
                from_x = (freq * self.graph_offset)
            
    
            to_x = (freq+1) * self.graph_offset
            to_y = self._get_y_cpu(pcpu)
                
            # Debug context, just for development
            #self.check_context(event, buffer_offset, length, freq)
            
            self.dat.draw_line(context, from_x, from_y, to_x, to_y)
            buffer_offset+=1
            freq+=1
        
        context.stroke()

"""
window = gtk.Window()
window.add(XO_CPU())
window.set_size_request(gtk.gdk.screen_width() * 85 / 100, 400)
window.show_all()
gtk.main()
"""